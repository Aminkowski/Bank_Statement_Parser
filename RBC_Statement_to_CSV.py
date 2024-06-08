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
    """unfortunately I haven't found a way to make this part neat and intuitive. 
        Transactions usually have an ID, so I filtered them based on that.
        the only exceptions that I've found to this are the inlurance premium and it's tax.
        Then there is the metadata that comes with each statement. 
        in the case of the final and initial balance it's just a straightforward matching.
        for the minimum balance there always seems to be a null string associate with an instance of it.
        for the credit limit and remaining balance it seems to suffices to look for an associated keyword in the preceding text.
        For now I've cut some corners by letting 
        Availablecredit, Payments&credits, Purchases&debits, Cashadvances, Interest, Fees
        be caught by a len < 20 rule. it's arbitrary and error prone so this is where i need to look if something funki is going on.
        FOR EXAMPLE CAN CATCH A NONSENSE DESCRIPTION THAT IS <20 LENGTH
        or can dismiss an appropriate description that is longer than 20 characters
        the latter is however caught by the acctDict function, where
        if a long description item has a unique cost associated with it we get a runtime error.
        so really I just need to be paranoid about the first case
        """
    # Transactions
    idmatch = re.search(r"\d{23}", item[0]) # assuming (23 digits = id) and (id iff a transaction)
    if idmatch:   # transactions first because most common
        id = idmatch.group(0)
        impure_desc = item[0].split(id)[0]
        if len(impure_desc) > 50:
            cleaner_desc = impure_desc.split("DATEDATE")[1] # if no datedate, then error
            return [cleaner_desc, item[1], True]
        return [impure_desc, item[1], True]
    # ALL OF THE BELOW TRANSACTIONS CAN BE CRINGE IF AT THE BEGINNING OF THE PAGE.
    elif item[0][10:] == "BALANCEPROTECTORPREMIUM" or item[0][10:] == "PROVINCIALTAX" or item[0].find("ANNUALFEE") >= 0:
        return [item[0], item[1], True]
    elif item[0].find("FIRSTREPORT") >= 0:
        return [item[0][0:21], item[1], True]
    elif item[0].find("CASHADVANCEINTEREST") >= 0 or item[0].find("PURCHASEINTEREST") >= 0:
        return [item[0], item[1], True]
    #               HENCE THIS. i wish i could avoid this nicely.
    elif item[0].endswith("BALANCEPROTECTORPREMIUM"):
        n = item[0].find("BALANCEPROTECTORPREMIUM")
        return [item[0][n-10:], item[1], True]
    # ClosingAccountBalance
    elif item[0] == "NEWBALANCE" or item[0] == "ClosingAccountBalance" or item[0] == "CREDITBALANCE":
        return ["ClosingBalance", item[1], False]
    # PreviousAccountBalance
    elif item[0] == "PREVIOUSACCOUNTBALANCE" or item[0] == "PREVIOUSSTATEMENTBALANCE":
        return ["PreviousBalance", item[1], False]
    # MinimumPayment
    elif item[0] == "":
        return ["MinimumPayment", item[1], False]
    # Availablecredit, Payments&credits, Purchases&debits, Cashadvances, Interest, Fees
    elif len(item[0]) < 21:
        return [item[0], item[1], False]
    # CreditLimit
    elif item[0].find("Creditlimit") >= 0:
        return ["CreditLimit", item[1], False]
    elif item[0].find("Remaining") >= 0:
        return ["RemainingBalance", item[1], False]
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
    # if os.path.isfile(file):
    #     print('processing: ', file)
    # else:
    #     raise RuntimeError('not a file')
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

def acctDict(acct):
    """Turns non-transaction entries into a dict of acct infos, after checking the "redundant" entries are clear"""
    dux = []
    leg = []
    for x in acct:
        if len(x[0]) > 20:
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
            if r[0] == "SUBTOTALOFMONTHLYACTIVITY":    # only appears when got a new CC.
                continue    # useless info, except maybe to know CC changed
            raise RuntimeError(f"the item:\n{r}\n needs a label")
    # if here, no errors were found. so all dux are redundant and thrown out
    acctSummary = {}    # by making it a dict, repeat values are eliminated
    for pair in leg:
        acctSummary[pair[0]] = pair[1]
    return acctSummary

def reprParsed(trs, vals):
    print("TRANSACTIONS")
    for i in trs:
        print(i)
    print("ACCOUNT SUMMARY")
    for i in vals:
        print(i, vals[i])

def check(acct, trns):
    # Sum up transactions according to Summary Categories provided
    Payments = 0
    Purchases = 0
    # CashAdvances = 0
    # Interest = 0
    # Fees = 0
    for trn in trns:
        # print(trn)
        # if trn[0].find("INTEREST") >= 0:
        #     Interest += trn[1]
        #     print(f"{trn} is an interest")
        # elif trn[0].find("SERVICECHARGE") >= 0 or trn[0].endswith("ANNUALFEE"):
        #     Fees += trn[1]
        #     print(f"{trn} is a Fee")
        # elif trn[0].find("ATMCASHADV") >= 0:
        #     CashAdvances += trn[1]
        #     print(f"{trn} is a Cash Advance")
        if trn[1] > 0:
            Purchases += trn[1]
        else:
            Payments -= trn[1]
    # for i in acct:
    #     print(i, acct[i])
    # Check sums match summary data
    # if abs(Purchases - acct["Purchases&debits"]) > 0.005:
    #     print(Purchases)
    #     print(acct["Purchases&debits"])
    #     raise RuntimeError("Potentially missed a purchase transaction")
    # elif abs(Payments + acct["Payments&credits"]) > 0.005:
    #     raise RuntimeError("Potentially missed a payment transaction")
    # elif abs(CashAdvances - acct["Cashadvances"]) > 0.005:
    #     raise RuntimeError("Potentially missed a Cash Advance transaction")
    # elif abs(Interest - acct["Interest"]) > 0.005:
    #     raise RuntimeError("Potentially missed an Interest Fee")
    # elif abs(Fees - acct["Fees"]) > 0.005:
    #     raise RuntimeError("Potentially missed a Fee")
    # else:
    delta = acct["ClosingBalance"] - acct["PreviousBalance"]
    allGood = True if abs(delta - (Purchases - Payments)) < 0.005 else False
    if allGood:
        print("All transactions have been accounted for")
    else:
        raise RuntimeError("Potentially missed a transaction")

def main(file):
    print(file)
    transactions, accountdata = PDFtoLists(file)
    acctVals = acctDict(accountdata)
    check(acctVals, transactions)
    # if any mistakes have happened, the above will throw a runtime error
    trdf = pd.DataFrame(transactions)
    acctdf = pd.Series(acctVals, name='amount')
    # print(len(trdf), len(acctdf))
    date = re.search(r"\d{4}-\d{2}-\d{2}", file).group(0)
    trdf.to_csv(f"../CC_Transaction_CSVs/CC_{date}.csv")
    acctdf.to_csv(f"../CC_MetaData_CSVs/CCdata_{date}.csv")
    # reprParsed(transactions, acctVals)
    return (trdf, acctdf)

# sfile =  # put particular statement here
# main(sfile)
# transactions, accountdata = PDFtoLists(sfile)
# print("transasctions")
# for tr in transactions:
#     print(tr)
# print("account data")
# for da in accountdata:
#     print(da)
# print(len(accountdata))
# actd = acctDict(accountdata)
# for i in actd:
#     print(i, actd[i])
# print(f"length of the dict = {len(actd)}")
