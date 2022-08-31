from  base64 import b64encode,b64decode
from  backend.main.store import secret_registry
from  Crypto.Random import get_random_bytes
from  Crypto.Cipher import AES
import jsons

class Ballot:
    """
    A ballot that exists in a specific, secret manner
    """
    def __init__(self, ballot_number: str, chosen_candidate_id: str, voter_comments: str):
        self.ballot_number = ballot_number
        self.chosen_candidate_id = chosen_candidate_id
        self.voter_comments = voter_comments


def generate_ballot_number(national_id:str) -> str:

    """
    Produces a ballot number. Feel free to add parameters to this method, if you feel those are necessary.

    Remember that ballot numbers must respect the following conditions:

    1. Voters can be issued multiple ballots. This can be because a voter might make a mistake when filling out one
       ballot, and therefore might need an additional ballot. However it's important that only one ballot per voter is
       counted.
    2. All ballots must be secret. Voters have the right to cast secret ballots, which means that it should be
       technically impossible for someone holding a ballot to associate that ballot with the voter.
    3. In order to minimize the risk of fraud, a nefarious actor should not be able to tell that two different ballots
       are associated with the same voter.

    :return: A string representing a ballot number that satisfies the conditions above
    
    """
    national_id = national_id.replace("-", "").replace(" ", "").strip()
    expected_bytes=16
    
    encryption_key= secret_registry.get_secret_bytes("ballot_number encryption key")
    if not encryption_key:
        encryption_key = get_random_bytes(expected_bytes * 2)
        secret_registry.overwrite_secret_bytes("ballot_number encryption key", encryption_key)
    
    nonce           = get_random_bytes(expected_bytes)
    cipher          = AES.new(encryption_key, AES.MODE_SIV, nonce=nonce)
    ciphertext, tag = cipher.encrypt_and_digest(national_id.encode("utf-8"))
    
    nonce_str        = b64encode(nonce).decode("utf-8")
    tag_str          = b64encode(tag).decode("utf-8")
    ciphertext_str   = b64encode(ciphertext).decode("utf-8")
    
    return nonce_str+"-"+tag_str+"-"+ciphertext_str
