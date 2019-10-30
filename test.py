import ethnologer

test = []
with open('../lrec-20/sorted-typ.txt', 'r') as f:
    temp = ''
    for line in f:
        try:
            temp_line = eval(line)
            test.append(temp_line[0])
        except:
            try:
                temp_line = eval(temp.strip() + line.strip())
                test.append(temp_line[0])
                temp = ''
            except:
                temp += line.strip()


typology = ethnologer.TypologicalRules('../lrec-20/min-parse.txt')
with open('output.txt', 'w') as f:
    for term in test:
        label = []
        for rule in typology.rules:
            if typology.satisfies(rule, term.lower()):
                label.append(rule)
        print(f'{term} : {label}\n')
        f.write(f'{term} : {label}\n')
