from typing import Set, Optional

from backend.main.objects.voter import Voter, BallotStatus,VoterStatus
from backend.main.objects.candidate import Candidate
from backend.main.objects.ballot import Ballot, generate_ballot_number
from backend.main import api,store
from backend.main.store.data_registry import VotingStore


def issue_ballot(voter_national_id: str) -> Optional[str]:
    """
    Issues a new ballot to a given voter. The ballot number of the new ballot. This method should NOT invalidate any old
    ballots. If the voter isn't registered, should return None.
    
    :params: voter_national_id The sensitive ID of the voter to issue a new ballot to.
    :returns: The ballot number of the new ballot, or None if the voter isn't registered
    """

    store = VotingStore.get_instance()
    
    votor_status=store.get_vote_status(voter_national_id)
    print("votor_status",votor_status)
    if(votor_status):
        # If the voter registered,Issues a new ballot to a given voter.
        ballot_id= generate_ballot_number(voter_national_id)
        #print("isuue:generate_ballot_numbe",ballot_id)
        
        store.new_ballot(voter_national_id,ballot_id)

        return(ballot_id)
    else:
        #If the voter isn't registered, should return None
        return(None)
    
def count_ballot(ballot: Ballot, voter_national_id: str) -> BallotStatus:
    """
    Validates and counts the ballot for the given voter. If the ballot contains a sensitive comment, this method will
    appropriately redact the sensitive comment.

    This method will return the following upon the completion:
    1. BallotStatus.FRAUD_COMMITTED - If the voter has already voted
    2. BallotStatus.VOTER_BALLOT_MISMATCH - The ballot does not belong to this voter
    3. BallotStatus.INVALID_BALLOT - The ballot has been invalidated, or does not exist
    4. BallotStatus.BALLOT_COUNTED - If the ballot submitted in this request was successfully counted
    5. BallotStatus.VOTER_NOT_REGISTERED - If the voter is not registered

    :param: ballot The Ballot to count
    :param: voter_national_id The sensitive ID of the voter who the ballot corresponds to.
    :returns: The Ballot Status after the ballot has been processed
    """
    store = VotingStore.get_instance()
    
    voter=store.get_vote(voter_national_id)
    if voter==None:
         return(BallotStatus.VOTER_NOT_REGISTERED)
    
     
    voter_status=store.get_vote_status(voter_national_id)
    print("voter_status---->",voter_status)
    ballot_status=store.get_ballot(ballot.ballot_number)
    print("ballot_status===>",ballot_status)
    
    check_vote_ballot=store.check_specifically_and_valid(voter_national_id,ballot.ballot_number)

    if not check_vote_ballot:
        return(BallotStatus.VOTER_BALLOT_MISMATCH)
    
    
    if BallotStatus(ballot_status)==BallotStatus.VOTER_NOT_REGISTERED:
        store.registory_ballot(ballot,str(BallotStatus.VOTER_NOT_REGISTERED.value),voter_national_id,voter)
        
        if VoterStatus(voter_status) == VoterStatus.REGISTERED_NOT_VOTED :
            store.update_vote_status(voter_national_id,str(VoterStatus.BALLOT_COUNTED.value))
            store.update_ballot_status(ballot.ballot_number,str(BallotStatus.BALLOT_COUNTED.value))
            return(BallotStatus.BALLOT_COUNTED)
            
        elif VoterStatus(voter_status) == VoterStatus.BALLOT_COUNTED:
            store.update_vote_status(voter_national_id,str(VoterStatus.FRAUD_COMMITTED.value))
            store.update_ballot_status(ballot.ballot_number,str(BallotStatus.FRAUD_COMMITTED.value))
            return(BallotStatus.FRAUD_COMMITTED)
        
        elif VoterStatus(voter_status) == VoterStatus.FRAUD_COMMITTED:    
            return(BallotStatus.FRAUD_COMMITTED)
    
        
    elif BallotStatus(ballot_status)==BallotStatus.BALLOT_COUNTED :
        store.update_vote_status(voter_national_id,str(VoterStatus.FRAUD_COMMITTED.value))
        store.update_ballot_status(ballot.ballot_number,str(BallotStatus.FRAUD_COMMITTED.value))
        return(BallotStatus.FRAUD_COMMITTED )
    
    elif BallotStatus(ballot_status)==BallotStatus.INVALID_BALLOT :
        return(BallotStatus.INVALID_BALLOT)
    

   
def invalidate_ballot(ballot_number: str) -> bool:
    """
    Marks a ballot as invalid so that it cannot be used. This should only work on ballots that have NOT been cast. If a
    ballot has already been cast, it cannot be invalidated.

    If the ballot does not exist or has already been cast, this method will return false.

    :returns: If the ballot does not exist or has already been cast, will return Boolean FALSE.
              Otherwise will return Boolean TRUE.
    """
    store = VotingStore.get_instance()
    ballot_status=store.get_ballot(ballot_number)
   
    if ballot_status==None:
        return(False)
    
    elif BallotStatus(ballot_status)==BallotStatus.BALLOT_COUNTED:
        return(False)

    else:
        store.update_ballot_status(ballot_number,str(BallotStatus.INVALID_BALLOT.value))
        return(True)

def verify_ballot(voter_national_id: str, ballot_number: str) -> bool:
    """
    Verifies the following:

    1. That the ballot was specifically issued to the voter specified
    2. That the ballot is not invalid

    If all of the points above are true, then returns Boolean True. Otherwise returns Boolean False.

    :param: voter_national_id The id of the voter about to cast the ballot with the given ballot number
    :param: ballot_number The ballot number of the ballot that is about to be cast by the given voter
    :returns: Boolean True if the ballot was issued to the voter specified, and if the ballot has not been marked as
              invalid. Boolean False otherwise.
    """
    store = VotingStore.get_instance()
    count_ballot=store.check_specifically_and_valid (ballot_number,voter_national_id)
    
    print("check_specifically_and_valid",count_ballot)
    if count_ballot > 0:
        return False
    elif count_ballot == 0:
        return True
    
#
# Aggregate API
#

def get_all_ballot_comments() -> Set[str]:
    """
    Returns a list of all the ballot comments that are non-empty.
    :returns: A list of all the ballot comments that are non-empty
    """
    store = VotingStore.get_instance()
    return store.get_comments()

def compute_election_winner() -> Candidate:
    """
    Computes the winner of the election - the candidate that gets the most votes (even if there is not a majority).
    :return: The winning Candidate
    """
    store = VotingStore.get_instance()
    return store.get_winner()

def get_all_fraudulent_voters() -> Set[str]:
    """
    Returns a complete list of voters who committed fraud. For example, if the following committed fraud:

    1. first: "John", last: "Smith"
    2. first: "Linda", last: "Navarro"

    Then this method would return {"John Smith", "Linda Navarro"} - with a space separating the first and last names.
    """
    store = VotingStore.get_instance()
    return store.fraudulent_voters()

