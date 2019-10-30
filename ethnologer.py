import json
import pickle as pkl
import os
import argparse


'''
Ethnologue class becomes an easily searchable class of languages and families present in ethnologue
    -Can only index by the most parent family
    -Index language by language code
'''

class Ethnologue():
    def __init__(self, classifier, ethnologue_files):
        self.families = {}
        self.languages = {}
        self.classifer = classifier
        for fi in ethnologue_files:
            name = fi.split('/')[-1][:-5]
            content = open(fi, 'r').read()
            typ = self.get_typological_info(content)
            fams = self.get_family_info(content)
            self.build_language(name, fams)
        
            if typ != -1:
                features = classifier.get_features(typ)
                for f in features:
                    self.languages[name].add_typological_feature(f)

        for family in self.families:
            if self.families[family].common_typological_features is None:
                self.families[family].set_common_typological_features()

    def add_family(self, family):
        if family.name not in self.families:
            self.families[family.name] = family
            if family.parent_family is not None and family.parent_family not in self.families:
                self.add_family(family.parent_family)

    def add_language(self, language):
        self.languages[language.name] = language

    def build_families(self, fam):
        if fam[0] not in self.families:
            root  = LanguageFamily(fam[0])
        else:
            root = self.families[fam[0]]
        temp_fam = root
        for index, family in enumerate(fam[1:], 1):
            if family not in [daughter.name for daughter in temp_fam.daughter_families]:
                temp_fam = LanguageFamily(family, temp_fam)
            else:
                for d in temp_fam.daughter_families:
                    if family == d.name:
                        temp_fam = d
                        break
        self.add_family(root)
        return temp_fam

    def build_language(self, lang, fam):
        if fam != -1:
            parent = self.build_families(fam)
            self.add_language(Language(lang, parent))
            parent.add_member(self.languages[lang])
        else:
            parent = LanguageFamily('Unclassified')
            self.add_family(parent)
            self.add_language(Language(lang, parent))
            parent.add_member(self.languages[lang])

    def get_typological_info(self, content):
        typ = self.get_label(content, 'Typology')
        if typ is None:
            return -1
        typ = typ.split(';')
        for t in range(len(typ)):
            typ[t] = typ[t].replace('Typology', '')
            typ[t] = typ[t].replace('.', '')
            typ[t] = typ[t].strip()
        return typ
    
    def get_family_info(self, content):
        fam = self.get_label(content, 'Classification')
        if fam is None:
            return -1
        fam = fam.replace('Classification', '')
        fam = fam.split(',')
        for f in range(len(fam)):
            fam[f] = fam[f].strip()
        return fam

    # removes tags from html
    def remove_tags(self, content):
        PAUSE = False
        retVal = ''
        for c in content:
            if c == '<':
                PAUSE = True
            elif c == '>':
                PAUSE = False
            if not PAUSE and c != '>':
                retVal += c
        return retVal

    # parses ethnologue and gets the field (only typology or classification currently)
    def get_label(self, content, label):
        content = content.split('<div class="field-label">')
        for c in content:
            if label in c:
                return self.remove_tags(c)

'''
LanguageFamily class contains the references to find the members (languages who have this instance as a direct parent) and daughter families (families who have this as a direct parent)
    -common_typological_features is the intersection of all non-zero typological sets of members AND daughter families typological features

'''
class LanguageFamily():
    def __init__(self, name, parent_family=None):
        self.name = name
        self.members = []
        self.daughter_families = []
        self.parent_family = parent_family
        if self.parent_family is not None:
            self.parent_family.add_daughter(self)
        self.common_typological_features = None

    def add_member(self, language):
        self.members.append(language)

    def add_daughter(self, language_family):
        self.daughter_families.append(language_family)

    '''
        This makes the following assumptions:
            -if there are 0 typological features, it assumes ethnologue had no entry; unclassified
            -if there are any typological features, it assumes this is a complete list
            -if every member of a family (and all members of daughter families) share a feature, it is a universal/common/shared feature
            -if a feature is universal to a family, all [typologically] unclassified languages should have this feature.
    '''
    def set_common_typological_features(self):
        common = set()
        
        # if this family has member languages; intersect their features
        if len(self.members) != 0:
            for l in self.members:
                if len(common) == 0:
                    # only intersect non-zero sets
                    # if they are zero, it's likely because there was not a typology section in ethnologue
                    if len(l.typological_features) > 0:
                        common = l.typological_features
                else:
                    if len(l.typological_features) > 0:
                        common = common.intersection(l.typological_features)
        # if this family has daughter languages, intersect their common features
        if len(self.daughter_families) != 0:
            if len(common) == 0:
                # only intersect non-zero sets
                # if they are 0, it's likely because their members were unclassified
                # the above assumption may need to be revised since it could be that the daughter family has no universal features
                if self.daughter_families[0].common_typological_features is None:
                    self.daughter_families[0].set_common_typological_features()
                common = self.daughter_families[0].common_typological_features
            for d in self.daughter_families:
                if len(common) == 0:
                    if d.common_typological_features is None:
                        d.set_common_typological_features()
                    if len(d.common_typological_features) > 0:
                        common = d.common_typological_features
                else:
                    if d.common_typological_features is None:
                        d.set_common_typological_features()
                    if len(d.common_typological_features) > 0:
                        common = common.intersection(d.common_typological_features)
        self.common_typological_features = common

    def __str__(self):
        return self.name


'''
    Language has a parent family and typological features extracted from Ethnologue

'''
class Language():
    def __init__(self, name, parent_family=None):
        self.name = name
        self.typological_features = set()
        self.parent_family = parent_family
    
    def add_typological_feature(self, feature):
        self.typological_features.add(feature)


'''
    TypologicalRules takes in a pre-defined rule-set that was written based on the most common typological descriptions found on Ethnologue
        -determines if a given description satisfies any of these rules
        -currently does not have mutually-exclusive categories
'''
class TypologicalRules():
    def __init__(self, file_path):
        with open(file_path, 'r') as f:
            self.rules = json.loads(f.read())['rules']

    def satisfies(self, tag, description):
        # replaces A for S to be uniform in description
        good = ['svo', 'sov', 'osv', 'ovs', 'vso', 'vos']
        bad = ['avo', 'aov', 'oav', 'ova', 'vao', 'voa']
        for g in range(len(good)):
            description = description.replace(bad[g], good[g])

        if "contains" in self.rules[tag]:
            for c in self.rules[tag]["contains"]:
                CONT_SAT = True
                for term in c:
                    if term not in description:
                        CONT_SAT = False
                if CONT_SAT:
                    break
        NOT_CONT_SAT = True
        if "does not contain" in self.rules[tag]:
            for c in self.rules[tag]["does not contain"]:
                if c in description:
                    NOT_CONT_SAT = False
        return CONT_SAT and NOT_CONT_SAT

    def get_features(self, descriptions):
        retVal = []
        for d in descriptions:
            for r in self.rules:
                if r not in retVal:
                    if self.satisfies(r, d.lower()):
                        retVal.append(r)
        return retVal


def load_model(model_path):
    return pkl.load(open(model_path, 'rb'))

def save_model(model_path, typological_dict, ethnologue_paths):
    classifier = TypologicalRules(typological_dict)
    ethno = Ethnologue(classifier, ethnologue_paths)
    pkl.dump(ethno, open(model_path, 'wb'))
if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('typological_dict')
    parser.add_argument('--output', default='ethnologue.pkl')
    parser.add_argument('ethnologue_paths', nargs='*')

    args = parser.parse_args()
    save_model(args.output, args.typological_dict, args.ethnologue_paths)
    classifier = TypologicalRules(args.typological_dict)
    ethno = Ethnologue(classifier, args.ethnologue_paths)
    
    pkl.dump(ethno, open(args.output, 'wb'))
