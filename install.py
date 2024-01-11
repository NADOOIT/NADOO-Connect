import tkinter as tk
from tkinter import Label, Entry
import asyncio

from nadoo_connect.nadoo_email import *


class EmailAccountDialog(tk.simpledialog.Dialog):
    def body(self, master):
        self.entries = {}

        Label(master, text="POP Server:").grid(row=0)
        self.entries["pop_server"] = Entry(master)
        self.entries["pop_server"].grid(row=0, column=1)

        Label(master, text="POP Port:").grid(row=1)
        self.entries["pop_port"] = Entry(master)
        self.entries["pop_port"].grid(row=1, column=1)

        Label(master, text="SMTP Server:").grid(row=2)
        self.entries["smtp_server"] = Entry(master)
        self.entries["smtp_server"].grid(row=2, column=1)

        Label(master, text="SMTP Port:").grid(row=3)
        self.entries["smtp_port"] = Entry(master)
        self.entries["smtp_port"].grid(row=3, column=1)

        Label(master, text="Password:").grid(row=4)
        self.entries["password"] = Entry(master, show="*")
        self.entries["password"].grid(row=4, column=1)

        Label(master, text="Email:").grid(row=5)
        self.entries["email"] = Entry(master)
        self.entries["email"].grid(row=5, column=1)

        return self.entries["pop_server"]  # Initial focus

    def apply(self):
        self.result = {key: entry.get() for key, entry in self.entries.items()}


def get_email_account_from_user():
    def run_dialog():
        root = tk.Tk()
        root.withdraw()  # Hide the main window
        dialog = EmailAccountDialog(root, title="Enter Email Account Details")
        result = dialog.result
        root.destroy()
        return result

    email_account = run_dialog()
    return email_account


def main():
    setup_database(email_account_db_name="email_account.db")

    email_account = get_email_account_from_user()
    print(email_account)
    if email_account:
        # Set as default email account based on user input
        email_account[
            "is_default"
        ] = True  # Or use logic to determine if it should be default

        asyncio.run(
            save_email_account(
                email_account_db_name="email_account.db", email_account=email_account
            )
        )


if __name__ == "__main__":
    main()
