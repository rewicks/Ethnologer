# Build:

You can build a new ethnologue::

```python
import ethnologer
ethnologer.save_model(model_path, typological_rules_path, ethnologue_paths)

# for example:
ethnologer.save_model('ETHNOLOGUE', 'min-parse.txt', glob.glob('ethnologue/*'))

```

# Load

You can import ethnologer, and then load a saved model:
```python
import ethnologer

ethnologue = ethnologer.load_model(model_path)
```

Then you can get a language:
```python
ethnologue.languages['eng']
```
From the language, you can get the parent family, or the typological features:
```python
eng = ethnologue.languages['eng']
eng.typological_features # {'SVO', 'CAUSATIVES', ... }
eng.parent_family # 'ENGLISH' <-- LanguageFamily Class
```

You can also find a language family (provided it is the most senior language family in its family:

```python
ethnologue.families['Indo-European'] # correct!
ethnologue.families['Germanic'] # throws error
```
You can find a daughter family, by accessing the daughter family list:
```python
indo_eur = ethnologue.families['Indo-European']
indo_eur.daughter_families # ['Albanian', 'Germanic', ....] <--each is a LanguageFamily
indo_eur.common_typological_features # {'SVO'}
```
