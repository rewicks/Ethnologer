import json
import pickle as pkl
import os
import argparse

class Ethnologue():
    def __init__(self):
        self.families = {}
        self.languages = {}

    def add_family(self, family):
        if family.name not in self.families:
            self.families[family.name] = family
            if family.parent_family is not None and family.parent_family not in self.families:
                self.add_family(family.parent_family)

    def add_language(self, language):
        self.languages[language.name] = language

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

    def set_common_typological_features(self):
        if len(self.members) == 0 and len(self.daughter_families) == 0:
            print(self.name)
        else:
            if len(self.members) != 0:
                common = self.members[0].typological_features
                for l in self.members:
                    if l.typological_features is None:
                        l.set_common_typological_features()
                    common.intersection(l.typological_features)
            if len(self.daughter_families) != 0:
                if common is not None:
                    if self.daughter_families[0].common_typological_featues is not None:
                        self.daughter_families[0].set_common_typological_features()
                    common = self.daughter_families[0].common_typological_features
                for d in self.daughter_families:
                    if d.common_typological_features is not None:
                        d.set_common_typological_features()
                    common = common.intersection(d.common_typological_features)
            
            self.common_typological_features = common


# typological features should be a python set
class Language():
    def __init__(self, name, parent_family=None):
        self.name = name
        self.typological_features = set()
        self.parent_family = parent_family
    
    def add_typological_feature(self, feature):
        self.typological_features.add(feature)

class TypologicalRules():
    def __init__(self, file_path):
        with open(file_path, 'r') as f:
            self.rules = json.loads(f.read())['rules']

    def satisfies(self, tag, description):
        
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

def remove_tags(content):
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

def get_label(content, label):
    content = content.split('<div class="field-label">')
    for c in content:
        if label in c:
            return remove_tags(c)

def add_language_to_family(language, family):
    families_file = open('families.pkl', 'rb')
    family_dict = pkl.load(families_file)
    if language not in family_dict[family]:
        family_dict[family].append(language)
    families_file.close()
    families_file = open('families.pkl', 'wb')
    pkl.dump(family_dtc, families_file)

def get_typological_info(content):
    typ = get_label(content, 'Typology')
    if typ is None:
        return -1
    typ = typ.split(';')
    for t in range(len(typ)):
        typ[t] = typ[t].replace('Typology', '')
        typ[t] = typ[t].replace('.', '')
        typ[t] = typ[t].strip()
    return typ
    
def get_family_info(content):
    fam = get_label(content, 'Classification')
    if fam is None:
        return -1
    fam = fam.replace('Classification', '')
    fam = fam.split(',')
    for f in range(len(fam)):
        fam[f] = fam[f].strip()
    return fam

def build_families(fam, ethno):
    root  = LanguageFamily(fam[0])
    temp_fam = root
    for index, family in enumerate(fam[1:], 1):
        temp_fam = LanguageFamily(family, temp_fam)
    ethno.add_family(root)
    return temp_fam

def build_language(lang, fam, ethno):
    if fam != -1:
        parent = build_families(fam, ethno)
        ethno.add_language(Language(lang, parent))
        parent.add_member(ethno.languages[lang])
          
    else:
        parent = LanguageFamily('Unclassified')
        ethno.add_family(parent)
        ethno.add_language(Language(lang, parent))
        parent.add_member(ethno.languages[lang])

if __name__ == '__main__':
    
    parser = argparse.ArgumentParser()
    parser.add_argument('typological_dict')
    parser.add_argument('ethnologue_paths', nargs='*')

    args = parser.parse_args()
    
    classifier = TypologicalRules(args.typological_dict)
    ethno = Ethnologue()

    for fi in args.ethnologue_paths:
        name = fi.split('/')[-1][:-5]
        content = open(fi, 'r').read()
        typ = get_typological_info(content)
        fams = get_family_info(content)
        build_language(name, fams, ethno)
        
        if typ != -1:
            features = classifier.get_features(typ)
            for f in features:
                ethno.languages[name].add_typological_feature(f)

    for family in ethno.families:
        if ethno.families[family].common_typological_features is None:
            ethno.families[family].set_common_typological_features()
    ''' 
    for lang in ethno.languages:
        if ethno.languages[lang].parent_family is not None:
            ethno.languages[lang].parent_family.set_common_typological_features()
    STOP = False
    while not STOP:
        STOP = True
        for family in ethno.families:
            if ethno.families[family].common_typological_features is not None:
                if ethno.families[family].parent_family is not None:
                    ethno.families[family].parent_family.set_common_typological_features()
            else:
                STOP = False
    '''
    pkl.dump(ethno, open('ethno.pkl', 'wb'))
