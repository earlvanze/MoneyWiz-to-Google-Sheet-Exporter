from __future__ import print_function
import pickle
import os.path
import csv
import json
import traceback
from tkinter import filedialog
from tkinter import *
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Google Sheets stuff
# You should change these to match your own spreadsheet
if os.path.exists('gsheet_id.txt'):
    with open('gsheet_id.txt', 'r') as file:
       json_repr = file.readline()
       data = json.loads(json_repr)
       GSHEET_ID = data["GSHEET_ID"]
       RANGE_NAME = data["RANGE_NAME"]
else:
    GSHEET_ID = '10PmGsjxMXvIMDIig1QiS-YVYxqOClZEvEu8B9Z69MeA'
    RANGE_NAME = 'Transactions!A:I'
    
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
]

def parse_csv():
    root = Tk()
    root.filename =  filedialog.askopenfilename(title = "Select file",filetypes = (("CSV files","*.csv"),("All files","*.*")))
#    root.filename = "Untitled.csv"
    print(root.filename)
    with open(root.filename, 'r') as csvfile:
        fieldnames = ("Name", "Current balance", "Account", "Transfers", "Description", "Merchant",
                      "Category", "Date", "Time", "Amount", "Currency", "Check #")
        reader = csv.DictReader(csvfile, fieldnames)
        next(reader, None)  # skip the headers

        output_data = []

        for row in reader:
            if not row["Name"]:
                try:
#                    if "ORIG CO NAME:" in row["Description"]:
#                        continue
                    data = []
                    data.append(row["Date"])
                    data.append(row["Account"])
                    data.append(row["Description"].split('WEB ID:')[0])
                    data.append(row["Merchant"])

                    # Split Amount column to Incomes and Expenses columns
                    if float(row["Amount"].replace(',', '')) > 0:
                        data.append(row["Amount"])
                        data.append("")
                    else:
                        data.append("")
                        data.append(row["Amount"])

                    # Business Category
                    if row["Account"] == "88 Madison Joint Account":
                        data.append("88 Madison Ave")
                    elif row["Account"] == "110 N Saddle Dr":
                        data.append("110 N Saddle Dr")
                    elif row["Account"] == "90 Madison Ave":
                        data.append("90 Madison Ave")
                    elif row["Account"] == "Your Second Home Checking":
                        data.append("Your Second Home")
#                    elif row["Account"] == "CIU 88 Estate LLC":
#                        data.append("88 Madison Ave")
                    elif row["Account"] == "ECO Systems Checking":
                        data.append("724 3rd Ave")
                    elif row["Account"] == "Your Second Home Checking":
                        data.append("Your Second Home")
                    elif row["Account"] == "Dover Holdings Checking":
                        data.append("3880 Dover St")
                    else:
                        data.append("")

                    # Autofill Category column
                    # Venmo cleaning transactions
                    if row["Account"] == "88 Madison Joint Account" and "VENMO PAYMENT" in row["Description"]:
                        data[2] = data[2].replace(" WEB ID: 3264681992", "")
                        if float(row["Amount"]) == -25:
                            data[2] += " - 1 hr cleaning"
                        else:
                            data[2] += " - {0} hrs cleaning".format(float(row["Amount"]) / -20.0) # number of hours @ $20/hr
                        data[3] = "Florence Odongo"
                        data.append("Cleaning & Maintenance")

                    # Airbnb or Homeaway Income
                    elif row["Account"] == "88 Madison Joint Account" and "AIRBNB PAYMENTS" in row["Description"]:
                        data[3] = "Airbnb"
                        data.append("Rental")
                    elif row["Account"] == "88 Madison Joint Account" and "VRBO" in row["Description"]:
                        data.append("Rental")

                    # Mortgage Transactions
                    elif "DITECH" in row["Description"]:
                        data[3] = "Ditech Financial"
                        data.append("Mortgage")
                    elif "NewRez" in row["Description"]:
                        data[3] = "NewRez LLC"
                        data.append("Mortgage")

                    # Subscriptions: PriceLabs, Smartbnb, Arcadia, Netflix, TWC, BillFixers, Comcast, RedPocket, Tello
                    elif "PRICELABS" in row["Description"]:
                        data[3] = "PriceLabs"
                        data.append("Advertising")
                    elif "SMARTBNB" in row["Description"]:
                        data[3] = "Smartbnb"
                        data.append("Advertising")
                    elif "ARCADIA" in row["Description"]:
                        data[3] = "Arcadia Power"
                        data.append("Utilities")
                    elif "NETFLIX" in row["Description"]:
                        data[3] = "Netflix"
                        data.append("Subscriptions")
                    elif "TWC" in row["Description"]:
                        data[3] = "Spectrum"
                        data.append("Utilities")
                    elif "COMCAST" in row["Description"]:
                        data.append("Utilities")
                    elif "BILLFIXERS" in row["Description"]:
                        data[3] = "BillFixers"
                        data.append("Utilities")
                    elif "RED POCKET" in row["Description"]:
                        data.append("Utilities")
                    elif "TELLO" in row["Description"]:
                        data.append("Utilities")

                    # Gas/Fuel
                    elif "CONOCO" in row["Description"]:
                        data[3] = "Conoco"
                        data.append("Automobile > Gas/Fuel")

                    elif "Target" in row["Merchant"] or "Walmart" in row["Merchant"] or "Amazon" in row["Merchant"]:
                        data.append("Supplies")

                    elif "Instacart" in row["Merchant"]:
                        data.append("Food & Dining > Groceries")

                    # Payroll
                    elif "GUSTO" in row["Description"]:
                        data[3] = "Gusto"
                        data.append("Salary/Wages")

                    # Automatic Payments
                    elif "AUTOPAY" in row["Description"] or "AUTOMATIC PAYMENT" in row["Description"]:
                        data[3] = "Payment"
                        data[6] = "Personal"
                        data.append("Transfer")

                    elif row["Transfers"]:
                        data.append("Transfer")

                    else:
                        data.append(row["Category"])
                    print(data)
                    output_data.append(data)
                except:
                    traceback.print_exc()
                    continue
            else:
                next(reader, None)  # not transaction data, skip the row


    result = append_to_gsheet(output_data, GSHEET_ID, RANGE_NAME)
    return result


def append_to_gsheet(output_data=[], gsheet_id = GSHEET_ID, range_name = RANGE_NAME):
    creds = None
    # The file token.pickle stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server()
        # Save the credentials for the next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    service = build('sheets', 'v4', credentials=creds)

    # Call the Sheets API
    body = {
        'values': output_data
    }
    try:
        result = service.spreadsheets().values().append(
            spreadsheetId=gsheet_id, range=range_name,
            valueInputOption='USER_ENTERED', body=body).execute()
        message = ('{0} rows updated.'.format(DictQuery(result).get('updates/updatedRows')))
        return message
    except Exception as err:
        traceback.print_exc()
        return json.loads(err.content.decode('utf-8'))['error']['message']


# Used to search for keys in nested dictionaries and handles when key does not exist
# Example: DictQuery(dict).get("dict_key/subdict_key")
class DictQuery(dict):
    def get(self, path, default = None):
        keys = path.split("/")
        val = None

        for key in keys:
            if val:
                if isinstance(val, list):
                    val = [ v.get(key, default) if v else None for v in val]
                else:
                    val = val.get(key, default)
            else:
                val = dict.get(self, key, default)

            if not val:
                break;

        return val


print(parse_csv())
