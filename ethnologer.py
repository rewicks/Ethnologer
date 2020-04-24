from __future__ import annotations

import argparse
import glob
import json
import pickle as pkl
import re
from dataclasses import field, dataclass
from pathlib import Path
from typing import Optional, List, Any, Dict, MutableSet

import tqdm  # type: ignore


class HtmlParser:
    @staticmethod
    def remove_tags(text):
        """Remove tags from HTML."""
        # See https://medium.com/@jorlugaqui/how-to-strip-html-tags-from-a-string-in-python-7cb81a2bbf44
        clean = re.compile("<.*?>")
        return re.sub(clean, "", text)

    @staticmethod
    def get_label(content: str, label: str) -> Optional[str]:
        """Parse Ethnologue and gets the field (only typology or classification currently)"""
        parts = content.split('<div class="field-label">')
        for c in parts:
            if label in c:
                return HtmlParser.remove_tags(c)
        else:
            return None  # TODO(adm) raise an exception and have this return str.

    @staticmethod
    def get_typological_info(content) -> Optional[List[str]]:
        typ_ = HtmlParser.get_label(content, "Typology")
        if typ_ is None:
            return None
        typ = [t.replace("Typology", "").replace(".", "").strip() for t in (typ_.split(";"))]
        return typ

    @staticmethod
    def get_family_info(content: str) -> Optional[List[str]]:
        fam_ = HtmlParser.get_label(content, "Classification")
        if fam_ is None:
            return None
        fam_ = fam_.replace("Classification", "")
        fam = [f.strip() for f in (fam_.split(","))]
        return fam

    @staticmethod
    def get_speaker_info(content) -> Optional[int]:
        pop_ = HtmlParser.get_label(content, "Population")
        if pop_ is None:
            return None
        pop_ = pop_.replace("Population", "")
        if "no known" in pop_.lower():
            return 0
        parentheticals = re.findall("\([^)]*\)", pop_)
        for p in parentheticals:
            if "L1" not in p:
                pop_ = pop_.replace(p, "")
        pop = pop_.split(".")
        for p in range(len(pop)):
            pop[p] = pop[p].strip().replace(",", "")
            if "L1" in pop[p]:
                pop[p] = "L1".join([""] + pop[p].split("L1")[1:])
                if "L2" in pop[p]:
                    pop[p] = pop[p].split("L2")[0]
        L1 = False
        speakers = 0
        for p in pop:
            if "L1" in p:
                if not L1:
                    speakers = 0
                L1 = True
                res = re.findall(r"\d+", p)
                # res = [int(i) for i in p.split() if i.isdigit()]
                for r in res:
                    if int(r) > speakers:
                        speakers = int(r)
            if not L1:
                res = re.findall(r"\d+", p)
                # res = [int(i) for i in p.split() if i.isdigit()]
                for r in res:
                    if int(r) > speakers:
                        speakers = int(r)
        return speakers


class Ethnologue:
    """
    Ethnologue class becomes an easily searchable class of languages and families present in ethnologue
        -Can only index by the most parent family
        -Index language by language code
    """

    def __init__(
            self,
            classifier: TypologicalRules,
            ethnologue_files: Path,
            merge_from_path: Optional[Path] = None,
    ):
        self.families: Dict[str, LanguageFamily] = {}
        self.languages: Dict[str, Language] = {}
        self.classifier: TypologicalRules = classifier
        for fi_ in tqdm.tqdm(sorted(glob.glob(str(ethnologue_files)))):
            self.parse_ethnologue_html(classifier, fi_)

        if merge_from_path is not None:
            with open(merge_from_path) as merge:
                for line in merge:
                    try:
                        feature, languages = line.strip().split(":")
                        for lang in languages.strip().split(";"):
                            if lang in self.languages:
                                self.languages[lang].add_typological_feature(
                                    feature.strip()
                                )
                            else:
                                print(f"{lang} not in ethnologue")
                    except:
                        print(line)

        for family in self.families:
            if self.families[family].common_typological_features is None:
                self.families[family].set_common_typological_features()

        self.reconstruct()

    def parse_ethnologue_html(self, classifier: TypologicalRules, fi_: str) -> Language:
        fi = Path(fi_)
        name = fi.stem
        content = fi.read_text()
        typ = HtmlParser.get_typological_info(content)
        families = HtmlParser.get_family_info(content)
        pop = HtmlParser.get_speaker_info(content)

        if families is not None:
            print(name, pop)
        self.build_language(name, families)
        if typ is not None:
            features = classifier.get_features(typ)
            for f in features:
                self.languages[name].add_typological_feature(f)
        self.languages[name].speakers = pop if pop is not None else -1
        print(name, self.languages[name].speakers, pop)
        return self.languages[name]

    def add_family(self, family):
        if family.name not in self.families:
            self.families[family.name] = family
            if (
                    family.parent_family is not None
                    and family.parent_family not in self.families
            ):
                self.add_family(family.parent_family)

    def add_language(self, language: Language) -> None:
        self.languages[language.name] = language
        if language.parent_family is None:
            if "Unclassified" in self.families:
                self.families["Unclassified"] = LanguageFamily("Unclassified")
            self.families["Unclassified"].add_member(language)

    def build_families(self, fam):
        root = self.families.get(fam[0], LanguageFamily(fam[0]))
        temp_fam = root
        for subfamily in fam[1:]:
            if subfamily not in [daughter.name for daughter in temp_fam.daughter_families]:
                temp_fam = LanguageFamily(subfamily, parent_family=temp_fam)
            else:
                for d in temp_fam.daughter_families:
                    if subfamily == d.name:
                        temp_fam = d
                        break
        self.add_family(root)
        return temp_fam

    def build_language(self, lang: str, fam: Optional[List[str]]):
        if fam is not None:
            parent = self.build_families(fam)
            self.add_language(Language(lang, parent_family=parent))
            parent.add_member(self.languages[lang])
        else:
            parent = LanguageFamily("Unclassified")
            self.add_family(parent)
            self.add_language(Language(lang, parent_family=parent))
            parent.add_member(self.languages[lang])

    def reconstruct(self):
        for l in self.languages:
            if len(self.languages[l].typological_features) == 0:
                if self.languages[l].parent_family.name != "Unclassified":
                    self.languages[
                        l
                    ].reconstructed_typological_features = self.languages[
                        l
                    ].parent_family.common_typological_features.copy()
                else:
                    self.languages[l].reconstructed_typological_features = set()
            else:
                self.languages[l].reconstructed_typological_features = set()


@dataclass
class LanguageFamily:
    """
    LanguageFamily class contains the references to find the members (languages who have this instance as a direct
    parent) and daughter families (families who have this as a direct parent)
        -common_typological_features is the intersection of all non-zero
         typological sets of members AND daughter families typological features
    """

    name: str
    members: List[Language] = field(default_factory=list, repr=False)
    daughter_families: List[LanguageFamily] = field(default_factory=list, repr=False)
    parent_family: Optional[LanguageFamily] = field(default=None, repr=False)
    common_typological_features: Optional[Any] = None

    def __post_init__(self) -> None:
        if self.parent_family is not None:
            self.parent_family.add_daughter(self)

    def add_member(self, language: Language) -> None:
        self.members.append(language)

    def add_daughter(self, language_family: LanguageFamily) -> None:
        self.daughter_families.append(language_family)

    def set_common_typological_features(self):
        """
            This makes the following assumptions:
                -if there are 0 typological features, it assumes ethnologue had no entry; unclassified
                -if there are any typological features, it assumes this is a complete list
                -if every member of a family (and all members of daughter families) share a feature, it is a universal/common/shared feature
                -if a feature is universal to a family, all [typologically] unclassified languages should have this feature.
        """
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


@dataclass
class Language:
    """Language has a parent family and typological features extracted from Ethnologue"""

    name: str
    typological_features: MutableSet[str] = field(default_factory=set)
    parent_family: Optional[LanguageFamily] = None
    speakers: int = 0

    def add_typological_feature(self, feature):
        self.typological_features.add(feature)


class TypologicalRules:
    """
        TypologicalRules takes in a pre-defined rule-set that was written based on the most common typological descriptions found on Ethnologue
            -determines if a given description satisfies any of these rules
            -currently does not have mutually-exclusive categories
    """

    def __init__(self, file_path):
        with open(file_path, "r") as f:
            self.rules = json.loads(f.read())["rules"]

    def satisfies(self, cat, tag, description):
        # replaces A for S to be uniform in description
        good = ["svo", "sov", "osv", "ovs", "vso", "vos"]
        bad = ["avo", "aov", "oav", "ova", "vao", "voa"]
        for g in range(len(good)):
            description = description.replace(bad[g], good[g])
        if "contains" in self.rules[cat][tag]:
            for c in self.rules[cat][tag]["contains"]:
                CONT_SAT = True
                for term in c:
                    if term not in description:
                        CONT_SAT = False
                if CONT_SAT:
                    break
        NOT_CONT_SAT = True
        if "does not contain" in self.rules[cat][tag]:
            for c in self.rules[cat][tag]["does not contain"]:
                if c in description:
                    NOT_CONT_SAT = False
        return CONT_SAT and NOT_CONT_SAT

    def get_features(self, descriptions):
        retVal = []
        for cat in self.rules:
            temp = []
            for d in descriptions:
                for r in self.rules[cat]:
                    if r not in temp:
                        if self.satisfies(cat, r, d.lower()):
                            temp.append(r)
                            retVal.append(r)
            if len(temp) > 0:
                retVal.append("_AND_".join(sorted(temp)))
        return retVal


def load_model(model_path):
    return pkl.load(open(model_path, "rb"))


def save_model(
        output_file, typological_dict, ethnologue_paths, merge_from_path: Optional[Path] = None
):
    classifier = TypologicalRules(typological_dict)
    ethno = Ethnologue(classifier, ethnologue_paths, merge_from_path=merge_from_path)
    pkl.dump(ethno, open(output_file, "wb"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("typological_dict")
    parser.add_argument("--output", default="ethnologue.pkl")
    parser.add_argument("ethnologue_paths")

    args = parser.parse_args()
    save_model(args.output, args.typological_dict, args.ethnologue_paths)
