#
# This file contains classes that correspond to voters
#
from  base64 import b64encode,b64decode
from  backend.main.store import secret_registry
from  Crypto.Random import get_random_bytes
from  Crypto.Cipher import AES
import jsons
from random import shuffle
from enum import Enum


def obfuscate_national_id(national_id: str) -> str:
    """
    Minimizes a national ID. The minimization may be either irreversible or reversible, but one might make life easier
    that the other, depending on the use-cases.

    :param: national_id A real national ID that is sensitive and needs to be obfuscated in some manner.
    :return: An obfuscated version of the national_id.
    """
    national_id = national_id.replace("-", "").replace(" ", "").strip()
    sanitized_national_id = national_id[0]+"*******"+national_id[-1]

    return(sanitized_national_id)


def encrypt_name(name: str) -> str:
    """
    Encrypts a name, non-deterministically.

    :param: name A plaintext name that is sensitive and needs to encrypt.
    :return: The encrypted cipher text of the name.
    """
    expected_bytes =32
    
    encryption_key = secret_registry.get_secret_bytes("national id Encryption Key")
    if not encryption_key:
        encryption_key = get_random_bytes(expected_bytes * 2)
        secret_registry.overwrite_secret_bytes("national id Encryption Key", encryption_key)
    
    nonce   = get_random_bytes(expected_bytes)
    cipher  = AES.new(encryption_key, AES.MODE_SIV,nonce=nonce)
    cipher.update(b"")
    
    
    ciphertext, tag = cipher.encrypt_and_digest(name.encode("utf-8"))
    nonce_str        = b64encode(nonce).decode("utf-8")
    ciphertext_str  = b64encode(ciphertext).decode("utf-8")
    tag_str         = b64encode(tag).decode("utf-8")
    
    
    return jsons.dumps({'ciphertext': ciphertext_str, 'tag': tag_str, 'nonce': nonce_str})


def decrypt_name(encrypted_name: str) -> str:
    """
    Decrypts a name. This is the inverse of the encrypt_name method above.

    :param: encrypted_name The ciphertext of a name that is sensitive
    :return: The plaintext name
    """
    ciphertext_and_tag_strings = jsons.loads(encrypted_name)
    ciphertext  = b64decode(ciphertext_and_tag_strings['ciphertext'].encode("utf-8"))
    tag         = b64decode(ciphertext_and_tag_strings['tag'].encode("utf-8"))
    nonce       = b64decode(ciphertext_and_tag_strings['nonce'].encode("utf-8"))
    
  
    encryption_key = secret_registry.get_secret_bytes("national id Encryption Key")
    
    cipher = AES.new(encryption_key, AES.MODE_SIV, nonce=nonce)
    cipher.update(b"")
    
    return cipher.decrypt_and_verify(ciphertext, tag).decode("utf-8")




class MinimalVoter:
    """
    Our representation of a voter, with the national id obfuscated (but still unique).
    This is the class that we want to be using in the majority of our codebase.
    """
    def __init__(self, obfuscated_first_name: str, obfuscated_last_name: str, obfuscated_national_id: str):
        self.obfuscated_national_id = obfuscated_national_id
        self.obfuscated_first_name = obfuscated_first_name
        self.obfuscated_last_name = obfuscated_last_name


class Voter:
    """
    Our representation of a voter, including certain sensitive information.=
    This class should only be used in the initial stages when requests come in; in the rest of the
    codebase, we should be using the ObfuscatedVoter class
    """
    def __init__(self, first_name: str, last_name: str, national_id: str):
        self.national_id = national_id
        self.first_name = first_name
        self.last_name = last_name

    def get_minimal_voter(self) -> MinimalVoter:
        """
        Converts this object (self) into its obfuscated version
        """
        return MinimalVoter(
            encrypt_name(self.first_name.strip()),
            encrypt_name(self.last_name.strip()),
            obfuscate_national_id(self.national_id))


class VoterStatus(Enum):
    """
    An enum that represents the current status of a voter.
    """
    NOT_REGISTERED = "not registered"
    REGISTERED_NOT_VOTED = "registered, but no ballot received"
    BALLOT_COUNTED = "ballot counted"
    FRAUD_COMMITTED = "fraud committed"


class BallotStatus(Enum):
    """
    An enum that represents the current status of a voter.
    """
    VOTER_BALLOT_MISMATCH = "the ballot doesn't belong to the voter specified"
    INVALID_BALLOT = "the ballot given is invalid"
    FRAUD_COMMITTED = "fraud committed: the voter has already voted"
    VOTER_NOT_REGISTERED = "voter not registered"
    BALLOT_COUNTED = "ballot counted"


