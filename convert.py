import pandas as pd

df = pd.read_csv("collection.v2.added.csv")

df["SEX"].replace(["M", "F"], [1, 0], inplace=True)
df["SCH"].replace(["N", "V", "J"], [0, 1, 2], inplace=True)
df["COR"].replace(["A", "M", "S"], [0, 1, 2], inplace=True)
df["GRADE"].replace(["A+", "A", "B+", "B", "C+", "C", "D+",
                    "NG", "E"], [0, 1, 2, 3, 4, 5, 6, 7, 8], inplace=True)
# df["GRADE"].replace(["A+", "A", "B+", "B", "C+", "C", "D+",
#                     "NG", "E"], [0, 0, 1, 1, 2, 2, 3, 3, 3], inplace=True)

for ind in df.columns:
    if ind == "NAME" or ind == "ID" or ind == "SEX" or ind == "COR" or ind == "SCH" or ind == "GRADE" or ind == "CLASS" or ind == "AGE":
        continue
    else:
        df[ind].replace(["A", "B", "C", "D", "E"], [
                        0, 1, 2, 3, 4], inplace=True)
        df[ind].fillna(4, inplace=True)
        df.loc[(df[ind] != 0) & (df[ind] != 1) & (df[ind] != 2)
               & (df[ind] != 3) & (df[ind] != 4), ind] = 4

# df.drop(["NAME", "ID", "SEX", "AGE", "CLASS", "SCH", "2", "3", "5", "6", "7", "8", "9", "10", "12", "11", "15", "16", "17", "19",
#         "21", "22", "23", "24", "25", "26", "27", "28", "32",
#          "33", "34", "38", "39", "40", "41", "42"], axis='columns', inplace=True)

df.to_csv("/home/krishna/Desktop/collection.v2.new.csv", index=False)
