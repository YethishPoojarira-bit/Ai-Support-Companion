#!/usr/bin/env python3
"""
MailCrew - Email Processing Crew
"""

from mailcrew.crew import MailCrew, azure_llm

def run():
    """
    Run the MailCrew.
    """
    mail_crew = MailCrew()
    mail_crew.crew().kickoff(inputs={
        "recipient": "projectwork@gmail.com",
        "subject": "holiday update",
        "body": "i wanted you to know that guys tomorrow will be a fun day see u all tomorrow."
    })

if __name__ == '__main__':
    run()