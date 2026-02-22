import csv
with open(r'C:\Users\dines\Downloads\synthetic_banking_details_100000.csv', 'r') as f:
    reader = csv.reader(f)
    print("Header:", next(reader))
    print("Row 1:", next(reader))
