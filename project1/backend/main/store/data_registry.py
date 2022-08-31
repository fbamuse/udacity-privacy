#
# This file is the interface between the stores and the database
#

import sqlite3

from sqlite3 import Connection, Cursor, Row

from typing import List
from backend.main.objects.voter import Voter, VoterStatus,BallotStatus
from backend.main.objects.candidate import Candidate
from backend.main.objects.voter import VoterStatus
from backend.main.detection.pii_detection import redact_free_text
import os, traceback


class VotingStore:
    """
    A singleton class that encapsulates the interface between the stores and the databases.

    To use, simply do:

    >>> voting_store = VotingStore.get_instance()   # this will create the stores, if they haven't been created
    >>> voting_store.add_candidate(...)  # now, you can call methods that you need here
    """

    voting_store_instance = None

    @staticmethod
    def get_instance():
        if not VotingStore.voting_store_instance:
            VotingStore.voting_store_instance = VotingStore()

        return VotingStore.voting_store_instance

    @staticmethod
    def refresh_instance():
        """
        DO NOT MODIFY THIS METHOD
        Only to be used for testing. This will only work if the sqlite connection is :memory:
        """
        if VotingStore.voting_store_instance:
            VotingStore.voting_store_instance.connection.close()
        VotingStore.voting_store_instance = VotingStore()

    def __init__(self):
        """
        DO NOT MODIFY THIS METHOD
        DO NOT call this method directly - instead use the VotingStore.get_instance method above.
        """
        self.connection = VotingStore._get_sqlite_connection()
        self.create_tables()

    @staticmethod
    def _get_sqlite_connection() -> Connection:
        """
        DO NOT MODIFY THIS METHOD
        """
        #return sqlite3.connect(":memory:", check_same_thread=False)
        return sqlite3.connect(":memory:", check_same_thread=False)
     

    def create_tables(self):
        """
        Creates Tables
        """
        self.connection.execute(
            '''
            CREATE TABLE candidates (
                candidate_id integer primary key autoincrement,
                name text
                );
                '''
                )
        self.connection.execute(
            '''
            CREATE TABLE voter (
                voter_id integer primary key autoincrement,
                national_id text,
                first_name text,
                last_name text,
                status text,
                del_flag text
                );
                '''
                )
        self.connection.execute(
            '''CREATE TABLE ballot (
                ballot_id text,
                status text,
                candidate_id integer,
                vote text,
                national_id text,
                del_flag boolean 
                );
                ''')
        self.connection.commit()

    def add_candidate(self, candidate_name: str):
        """
        Adds a candidate into the candidate table, overwriting an existing entry if one exists
        """
        self.connection.execute("""INSERT INTO candidates (name) VALUES (?)""", (candidate_name, ))
        self.connection.commit()

    def get_candidate(self, candidate_id: str) -> Candidate:
        """
        Returns the candidate specified, if that candidate is registered. Otherwise returns None.
        """
        cursor = self.connection.cursor()
        cursor.execute('''SELECT * FROM candidates WHERE candidate_id=?''', (candidate_id,))
        candidate_row = cursor.fetchone()
        candidate = Candidate(candidate_id, candidate_row[1]) if candidate_row else None
        self.connection.commit()

        return candidate

    def get_all_candidates(self) -> List[Candidate]:
        """
        Gets ALL the candidates from the database
        """
        cursor = self.connection.cursor()
        cursor.execute("""SELECT * FROM candidates""")
        all_candidate_rows = cursor.fetchall()
        all_candidates = [Candidate(str(candidate_row[0]), candidate_row[1]) for candidate_row in all_candidate_rows]
        self.connection.commit()

        return all_candidates
    
    def add_Vote(self,voter:Voter) ->bool:
        #minimal_voter=Voter.get_minimal_voter(voter)
        try:
            cursor = self.connection.cursor()
            cursor.execute("""SELECT count(*) FROM voter WHERE national_id=?""", (voter.national_id,))
            check_already_vote = cursor.fetchone()
            
            
            print("count from vote",check_already_vote[0])
            
            
            if(check_already_vote[0]==0):
                    self.connection.execute(
                        '''INSERT INTO voter (
                            national_id,
                            first_name,
                            last_name,
                            status
                            ) VALUES (?,?,?,?)''', (voter.national_id,voter.first_name,voter.last_name,str(VoterStatus.REGISTERED_NOT_VOTED.value)))
                    self.connection.commit()
        
                    
                    
                    return True

            else:
                return False
        except sqlite3.IntegrityError as e:
            print('INTEGRITY ERROR\n')
            print(traceback.print_exc())
            return False
        
    def get_vote(self,national_id:str) :
        sanitized_national_id = national_id.replace("-", "").replace(" ", "").strip()
        cursor = self.connection.cursor()
        cursor.execute("""SELECT first_name,last_name FROM voter WHERE national_id=?""", (sanitized_national_id,))
        voterobject = cursor.fetchone()
        self.connection.commit()
        if voterobject:
            voter=Voter(voterobject[0],voterobject[1],national_id)
            return(voter)
        else:
            return(None)
        
    def get_vote_status(self,national_id:str) :
        sanitized_national_id = national_id.replace("-", "").replace(" ", "").strip()
        cursor = self.connection.cursor()
        cursor.execute("""SELECT status FROM voter WHERE national_id=?""", (sanitized_national_id,))
        voterobject = cursor.fetchone()
        self.connection.commit()
        if voterobject:
            return(voterobject[0])
        else:
            return(None)
    
    def delete_Vote(self,national_id):
        cursor = self.connection.cursor()
        if(VoterStatus(self.get_vote_status(national_id))== VoterStatus.FRAUD_COMMITTED):
            return False
        else:
            cursor.execute("""UPDATE voter SET  del_flag =? WHERE national_id=?""", (False, national_id))
            self.connection.commit()
            return True

        
    def check_specifically_and_valid(self,national_id,ballot_number):
        cursor = self.connection.cursor()
        cursor.execute(
            """SELECT count(*) FROM ballot WHERE national_id=? AND ballot_id=? """, (national_id, ballot_number))
        count_ballot = cursor.fetchone()
        self.connection.commit()
        return count_ballot[0]
         
                             
    def get_ballot(self,ballot_number):
        cursor = self.connection.cursor()
        cursor.execute("""SELECT status FROM ballot WHERE  ballot_id=?""", (ballot_number,))
        ballot_status = cursor.fetchone()
        self.connection.commit()
        print(ballot_status)
        if ballot_status:
            return(ballot_status[0])
        else:
            return(None)
    
    
    def registory_ballot(self,ballot,status,national_id,voter:Voter):        
        cursor = self.connection.cursor()
        cursor.execute("""update ballot 
                       set status=?,candidate_id=?,vote=?,national_id=?,del_flag=? WHERE ballot_id=? """,
                       (status,ballot.chosen_candidate_id,redact_free_text(ballot.voter_comments,voter.first_name,voter.last_name),national_id,False,ballot.ballot_number))
        #cursor.execute("""insert into ballot 
        #               (ballot_id,status,candidate_id,vote,national_id,del_flag) values(?,?,?,?,?,?)""",
                       
        self.connection.commit() 
        return(True)

    def new_ballot(self, national_id, ballot_number):
        self.connection.execute("""insert into ballot (ballot_id, national_id,status) VALUES (?, ?,?)""", (ballot_number,national_id,str(BallotStatus.VOTER_NOT_REGISTERED.value)))
        self.connection.commit()

    def update_ballot_status(self,ballot_id,status):        
        cursor = self.connection.cursor()
        cursor.execute("""update ballot SET status =? WHERE ballot_id=?""", (status,ballot_id,))
        self.connection.commit() 
        return(True)
    
    def update_vote_status(self,national_id,status):        
        cursor = self.connection.cursor()
        cursor.execute("""update voter SET status =? WHERE national_id=?""", (status,national_id,))
        self.connection.commit() 
        return(True)
    
    
        
    def get_comments(self) -> List[str]:
        cursor = self.connection.cursor()
        cursor.execute("""SELECT vote FROM ballot WHERE status=?""",(str(BallotStatus.BALLOT_COUNTED.value),) )
        all_comments = cursor.fetchall()
        all_comment = [ str(comment_row[0]) for comment_row in all_comments]
        self.connection.commit()

        return (all_comment)   
    
    
    def get_winner(self) :
        cursor = self.connection.cursor()
        cursor.execute("""select candidate_id,max(cnt) from (SELECT candidate_id, count(*) as cnt FROM ballot GROUP BY candidate_id )""", )
        candidate_id = cursor.fetchone()
  
        
        cursor.execute("""select name from  candidates  WHERE candidate_id=?""",(str(candidate_id[0])) )
        candidate_name = cursor.fetchone()   
      
        
        return(Candidate(str(candidate_id[0]),candidate_name[0])) 
    
    
    def fraudulent_voters(self):
        cursor = self.connection.cursor()    
        cursor.execute("""SELECT first_name, last_name FROM voter WHERE status=?""",(str(VoterStatus.FRAUD_COMMITTED.value),) )
        votername = cursor.fetchall()
        
        fraudulent_voters_list = [ str(row[0])+ " "+ str(row[1]) for row in votername]
        return fraudulent_voters_list
        self.connection.commit()
        
