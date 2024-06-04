import re
import os
import pandas as pd
from pdfminer.high_level import extract_text

def descval(text):
    """from text to list of dollar values and the preceding text (their description)"""
    amount = re.compile(r"-?\$\d*,?\d+\.\d{2}")
    split = amount.findall(text)
    temp = text
    dvplist = []
    for cost in split:
        pair = temp.split(cost, 1)
        dvplist.append( (pair[0], cost) )
        temp = pair[1]
    return dvplist

def condmod(item):
    """looks at a ("description", value) and uses conditionals to return better description"""
    idmatch = re.search(r"\d{23}", item[0]) # assuming (23 digits = id) and (id iff a transaction)
    if idmatch:   # transactions first because most common
        id = idmatch.group(0)
        impure_desc = item[0].split(id)[0]
        if len(impure_desc) > 50:
            cleaner_desc = impure_desc.split("DATEDATE")[1] # if no datedate, then error
            return [cleaner_desc, item[1], True]
        return [impure_desc, item[1], True]
    elif len(item[0]) > 70:
        return ["redundant", item[1], False]
    elif item[0] == "":
        return ["MinimumPayment", item[1], False]
    elif item[0] == "PREVIOUSACCOUNTBALANCE":
        return ["PreviousAccountBalance", item[1], False]
    elif item[0] == "NEWBALANCE":
        return ["ClosingAccountBalance", item[1], False]
    elif item[0] == "TOTALACCOUNTBALANCE" or item[0] == "TotalAccountBalance":
        return ["redundant", item[1], False]
    elif len(item[0].split("Credit")) > 1:
        return ["CreditLimit", item[1], False]
    else:
        return [item[0], item[1], False]

def cadtonum(dval):
    """takes a string representing a CAD value and turns it into a float"""
    intval = dval.partition('$')
    vallst = intval[2].split(',')   # 2 entry is number string.
    valstr = ""
    for g in vallst:
        valstr += g
    if intval[0]=='':
        dval = float(valstr)
    elif intval[0]=='-':
        dval = -1*float(valstr)
    else:
        print("ERROR: unexpected input")
    return dval

def PDFtoLists(file):
    """Just does all the stuff, to one statement, and returns the important content"""
    # first just checking file type
    if os.path.isfile(file):
        print('processing: ', file)
    else:
        print('not a file')
        return Null
    # if not broken, do stuff
    text = extract_text(file)   # pdf content into raw string
    dv = descval(text)
    temp = []   # somewhat refining the dv data
    for i in dv:
        temp.append(condmod(i))
    transactions = []
    accountdata = []
    for t in temp:
        if t[2]:
            transactions.append([t[0][10:], cadtonum(t[1]), t[0][0:5], t[0][5:10]])
        else:
            accountdata.append([t[0], cadtonum(t[1])])
    return (transactions, accountdata)

def notmissingacctdata(acct):
    dux = []
    leg = []
    for x in acct:
        if x[0] == "redundant":
            dux.append(x)
        else:
            leg.append(x)
    # print(len(leg))     # would be nice to make leg a dictionary
    for r in dux:
        isRedundant = False
        for h in leg:
            if r[1] == h[1]:
                isRedundant = True
        # isRedundant = False
        if not isRedundant:
            raise OSError   # jank
    # if here, no errors were found. so all dux are redundant and thrown out
    return leg


sfile = "file"
transactions, accountdata = PDFtoLists(sfile)
legit = notmissingacctdata(accountdata)

# print("TRANSACTIONS")
# for i in transactions:
#     print(i)

print("ACCOUNT STUFFS")
for i in legit:
    # if i[2] == False:
    #     continue
    print(i)
    # print(len(i[0]))
    # print(len(i))

# df = pd.DataFrame(Statement)
# print(len(df))
# df.to_csv('statement.csv')
