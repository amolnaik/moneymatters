import numpy as np
import pandas as pd

class Reformat():

    def __init__(self):
        pass


    def category_and_subcategory(self, df):

        df_changed = df

        # Wage and Salary -> Salary
        df_changed['subcategory'] = np.where((df_changed.category == 'Wage & Salary') & (df_changed.subcategory == 'Net Pay'), 'Monthly Fixed', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Wage & Salary') & (df_changed.subcategory == 'Overtime'), 'Bonus', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Wage & Salary') & (df_changed.subcategory == 'Net Pay'), 'Monthly Fixed', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Wage & Salary'), 'Salary', df_changed.category)

        # Automobile -> Mobility
        df_changed['subcategory'] = np.where((df_changed.category == 'Automobile') & (df_changed.subcategory == 'Car Payment'), 'EMI', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Automobile') & (df_changed.subcategory == 'Gasoline'), 'Fueling', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Automobile') & (df_changed.subcategory == 'Insurance'), 'Monthly Fixed', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Automobile') & (df_changed.subcategory == 'Parking'), 'Monthly Fixed', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Automobile'), 'Mobility', df_changed.category)

        # Groceries
        df_changed['subcategory'] = np.where((df_changed.category == 'Groceries'), 'Groceries', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Groceries'), 'Household', df_changed.category)

        # Bills
        df_changed['subcategory'] = np.where((df_changed.category == 'Bills') & (df_changed.subcategory == 'Cable/Satellite Television'), 'Television', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Bills') & (df_changed.subcategory == 'Cell Phone'), 'Telephone', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Bills') & (df_changed.subcategory == 'On-line/Internet Service'), 'Internet Services', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Bills') & (df_changed.subcategory == 'Water & Sewer'), 'Utilities', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Bills') & (df_changed.subcategory == 'Garbage & Recycle'), 'Utilities', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Bills') & (df_changed.subcategory == 'Health Club'), 'Membership Fees', df_changed.subcategory)

        # Baby
        df_changed['subcategory'] = np.where((df_changed.category == 'Baby') & (df_changed.subcategory == 'Medicare'), 'Medicines', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Baby') & (df_changed.subcategory == 'Entertainment'), 'Accessories', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Baby') & (df_changed.subcategory == 'Fees'), 'Membership', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Baby'), 'Household', df_changed.category)

        # Bank Charges
        df_changed['subcategory'] = np.where((df_changed.category == 'Bank Charges') & (df_changed.subcategory == 'Service charge'), 'Fees', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Bank Charges'), 'Finances', df_changed.category)

        # Credit Card
        df_changed['subcategory'] = np.where((df_changed.category == 'Credit Card Payments/Transfers'), 'Reimbursement', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Credit Card Payments/Transfers'), 'Bills', df_changed.category)

        # Clothing
        df_changed['subcategory'] = np.where((df_changed.category == 'Clothing'), 'Clothing', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Clothing'), 'Personal', df_changed.category)


        # Deposit
        df_changed['subcategory'] = np.where((df_changed.category == 'Deposit'), 'Deposits', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Deposit'), 'Finances', df_changed.category)

        # Dining Out
        df_changed['subcategory'] = np.where((df_changed.category == 'Dining Out'), 'Dining Out', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Dining Out'), 'Leisure', df_changed.category)

        # Education
        df_changed['subcategory'] = np.where((df_changed.category == 'Education') & (df_changed.subcategory == 'Tuition'), 'Fees', df_changed.subcategory)

        # Entertainment -> Leisure
        df_changed['category'] = np.where((df_changed.category == 'Entertainment'), 'Leisure', df_changed.category)

        # Food
        df_changed['subcategory'] = np.where((df_changed.category == 'Food'), 'Dining Out', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Food'), 'Leisure', df_changed.category)

        # Gifts
        df_changed['subcategory'] = np.where((df_changed.category == 'Gift'), 'Gifts', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Gifts'), 'Gifts', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Gift'), 'Leisure', df_changed.category)
        df_changed['category'] = np.where((df_changed.category == 'Gifts'), 'Leisure', df_changed.category)
        df_changed['subcategory'] = np.where((df_changed.category == 'Other Income'), 'Gifts', df_changed.subcategory)

        # Hobbies
        df_changed['subcategory'] = np.where((df_changed.category == 'Hobbies/Leisure') & (df_changed.subcategory == 'Books & Magazines'), 'Books', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Hobbies/Leisure') & (df_changed.subcategory == 'Cultural Events'), 'Events', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Hobbies/Leisure') & (df_changed.subcategory == 'Movies & Video Rentals'), 'Events', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Hobbies/Leisure') & (df_changed.subcategory == 'Sporting Events'), 'Events', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Hobbies/Leisure') & (df_changed.subcategory == 'Sporting Goods'), 'Clothing', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Hobbies/Leisure'), 'Leisure', df_changed.category)


        # Fees -> Uncategorized
        df_changed['category'] = np.where((df_changed.category == 'Fees'), 'Uncategorized', df_changed.category)
        df_changed['category'] = np.where((df_changed.category == 'Happy'), 'Uncategorized', df_changed.category)

        #
        df_changed['category'] = np.where((df_changed.category == 'Health-care'), 'Healthcare', df_changed.category)
        df_changed['category'] = np.where((df_changed.category == 'Home Improvement'), 'Household', df_changed.category)

        #Insurance
        df_changed['category'] = np.where((df_changed.category == 'Insurance') & (df_changed.subcategory == 'Automobile'), 'Mobility', df_changed.category)
        df_changed['subcategory'] = np.where((df_changed.category == 'Mobility') & (df_changed.subcategory == 'Automobile'), 'Insurance', df_changed.subcategory)

        df_changed['category'] = np.where((df_changed.category == 'Insurance') & (df_changed.subcategory == 'Health'), 'Healthcare', df_changed.category)
        df_changed['subcategory'] = np.where((df_changed.category == 'Healthcare') & (df_changed.subcategory == 'Health'), 'Insurance', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Insurance'), 'Insurance', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Insurance'), 'Healthcare', df_changed.category)

        # Investment
        df_changed['subcategory'] = np.where((df_changed.category == 'Investment Income'), 'Interest', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Investment Income'), 'Investment', df_changed.category)
        df_changed['subcategory'] = np.where((df_changed.subcategory == 'Loan Interest'), 'Interest', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.subcategory == 'Mortgage Interest'), 'Interest', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.subcategory == 'Student Loan Interest'), 'Interest', df_changed.subcategory)

        # Not an expense
        df_changed['category'] = np.where((df_changed.category == 'Not an Expense'), 'Funds Transfer', df_changed.category)

        #
        df_changed['subcategory'] = np.where((df_changed.category == 'Personal Care'), 'Medicines', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Personal Care'), 'Personal', df_changed.category)

        # Travel
        df_changed['subcategory'] = np.where((df_changed.category == 'Travel/Vacation') & (df_changed.subcategory == 'Food'), 'Food', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Travel/Vacation') & (df_changed.subcategory == 'Lodging'), 'Hotel', df_changed.subcategory)
        df_changed['subcategory'] = np.where((df_changed.category == 'Travel/Vacation') & (df_changed.subcategory == 'Travel'), 'Fare', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Travel/Vacation'), 'Travel', df_changed.category)

        # Utilities
        df_changed['subcategory'] = np.where((df_changed.category == 'Utilities'), 'Utilities', df_changed.subcategory)
        df_changed['category'] = np.where((df_changed.category == 'Utilities'), 'Bills', df_changed.category)

        return df_changed
