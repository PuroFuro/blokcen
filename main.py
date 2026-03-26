from flask import Flask, jsonify, request
import requests
import argparse
import datetime
import hashlib
import json
import binascii

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

app = Flask(__name__)

class Wallet:
    def __init__(self, name):
        self.name = name
        
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()

    def get_public_key_pem(self):
        return self.public_key.public_bytes(
            serialization.Encoding.PEM,
            serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')


class Transaction:
    def __init__(self, sender, receiver, amount, signature=""):
        self.sender = sender
        self.receiver = receiver
        self.amount = amount
        self.signature = signature

    def sign_transaction(self, private_key):
        message = f"{self.sender}{self.receiver}{self.amount}".encode('utf-8')
        
        sig_bytes = private_key.sign(
            message,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        self.signature = binascii.hexlify(sig_bytes).decode('utf-8')

    def verify_transaction(self):
        if self.sender == "SYSTEM":
            return True

        message = f"{self.sender}{self.receiver}{self.amount}".encode('utf-8')
        try:
            public_key = serialization.load_pem_public_key(self.sender.encode('utf-8'))
            sig_bytes = binascii.unhexlify(self.signature)
            
            public_key.verify(
                sig_bytes,
                message,
                padding.PSS(
                    mgf=padding.MGF1(hashes.SHA256()),
                    salt_length=padding.PSS.MAX_LENGTH
                ),
                hashes.SHA256()
            )
            return True
        except Exception:
            return False

    def to_dict(self):
        return {
            "sender": self.sender,
            "receiver": self.receiver,
            "amount": self.amount,
            "signature": self.signature
        }


class Block:
    def __init__(self, index, transactions, previous_hash):
        self.index = index
        self.timestamp = str(datetime.datetime.now())
        self.transactions = transactions
        self.nonce = 0
        self.previous_hash = previous_hash
        self.hash = self.calculate_hash()

    def calculate_hash(self):
        block = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [t if isinstance(t, dict) else t.to_dict() for t in self.transactions],
            "nonce": self.nonce,
            "previous_hash": self.previous_hash
        }
        block_string = json.dumps(block, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def mine_block(self, difficulty):
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
        print("Block successfully mined! Hash:", self.hash)


class Blockchain:
    def __init__(self):
        self.difficulty = 2
        self.pending_transactions = []
        self.chain = [self.init_genesis_block()]
        self.nodes = set()

    def init_genesis_block(self):
        genesis_message = "Genesis Block - Initialization of the network."
        genesis_initial_hash = hashlib.sha256(genesis_message.encode()).hexdigest()
        
        genesis_tx = {"sender": "SYSTEM", "receiver": "Genesis", "amount": 0, "signature": "0"}
        return Block(0, [genesis_tx], genesis_initial_hash)

    def get_latest_block(self):
        return self.chain[-1]

    def get_balance(self, public_key):
        balance = 3
        # Calculate balance from all processed blocks
        for block in self.chain:
            for tx in block.transactions:
                sender = tx.get('sender') if isinstance(tx, dict) else tx.sender
                receiver = tx.get('receiver') if isinstance(tx, dict) else tx.receiver
                amount = tx.get('amount') if isinstance(tx, dict) else tx.amount
                
                if sender == public_key:
                    balance -= amount
                if receiver == public_key:
                    balance += amount
                    
        # Subtract outgoing amounts in the pending pool (mempool) to prevent double-spending
        for tx in self.pending_transactions:
            sender = tx.get('sender') if isinstance(tx, dict) else tx.sender
            amount = tx.get('amount') if isinstance(tx, dict) else tx.amount
            if sender == public_key:
                balance -= amount
                
        return balance


# --- FLASK API ROUTES ---

parser = argparse.ArgumentParser(description="Start a Blockchain Node")
parser.add_argument('name', type=str, nargs='?', default='Anonymous', help='Name of the node owner')
parser.add_argument('port', type=int, nargs='?', default=5000, help='Port to run the server on')
args, unknown = parser.parse_known_args()

node_chain = Blockchain()
identity = Wallet(name=args.name)

@app.route('/profile', methods=['GET'])
def get_profile():
    return jsonify({
        'name': identity.name,
        'public_key': identity.get_public_key_pem(),
        'balance': node_chain.get_balance(identity.get_public_key_pem())
    })

@app.route('/block', methods=['GET'])
def get_chain():
    chain_data = []
    for block in node_chain.chain:
        chain_data.append({
            'index': block.index,
            'timestamp': block.timestamp,
            'transactions': block.transactions,
            'previous_hash': block.previous_hash,
            'hash': block.hash,
            'nonce': block.nonce
        })
    return jsonify({'length': len(chain_data), 'chain': chain_data})

@app.route('/mempool', methods=['GET'])
def get_mempool():
    return jsonify({'mempool': node_chain.pending_transactions})

@app.route('/transaction', methods=['POST'])
def execute_transaction():
    incoming_data = request.get_json()

    if not incoming_data or 'receiver' not in incoming_data or 'amount' not in incoming_data:
        return jsonify({"error": "Missing receiver or amount parameters."}), 400

    current_balance = node_chain.get_balance(identity.get_public_key_pem())
    if current_balance < incoming_data['amount']:
        return jsonify({'error': f"Insufficient balance ({current_balance}) to complete the transaction."}), 400

    new_tx = Transaction(
        sender=identity.get_public_key_pem(),
        receiver=incoming_data['receiver'],
        amount=incoming_data['amount']
    )
    new_tx.sign_transaction(identity.private_key)

    if not new_tx.verify_transaction():
        return jsonify({"error": "Cryptographic signature validation failed."}), 400

    node_chain.pending_transactions.append(new_tx.to_dict())

    for node in node_chain.nodes:
        try:
            requests.post(f"{node}/receive_transaction", json=new_tx.to_dict())
        except requests.exceptions.RequestException:
            continue

    return jsonify({
        "message": "Transaction signed and added to the mempool.",
        "signature": new_tx.signature
    }), 201

@app.route('/receive_transaction', methods=['POST'])
def receive_transaction():
    incoming_data = request.get_json()
    
    tx = Transaction(
        sender=incoming_data['sender'],
        receiver=incoming_data['receiver'],
        amount=incoming_data['amount'],
        signature=incoming_data['signature']
    )

    if not tx.verify_transaction():
        return jsonify({"error": "Invalid signature, transaction rejected."}), 400

    node_chain.pending_transactions.append(incoming_data)
    return jsonify({"message": "Transaction received and verified."}), 201

@app.route('/validate', methods=['POST'])
def validate_transaction():
    incoming_data = request.get_json()
    tx = Transaction(
        sender=incoming_data['sender'],
        receiver=incoming_data['receiver'],
        amount=incoming_data['amount'],
        signature=incoming_data['signature']
    )

    if tx.verify_transaction():
        return jsonify({"message": "Signature is valid."}), 200
    else:
        return jsonify({"error": "Signature is invalid."}), 400

@app.route('/mine', methods=['GET'])
def mine_mempool():
    if not node_chain.pending_transactions:
        return jsonify({"message": "No transactions in the mempool to mine."}), 400
    
    # Give the miner a reward of 67
    reward_tx = Transaction("SYSTEM", identity.get_public_key_pem(), 67)
    node_chain.pending_transactions.insert(0, reward_tx.to_dict())

    new_index = len(node_chain.chain)
    previous_hash = node_chain.get_latest_block().hash

    new_block = Block(
        index=new_index,
        transactions=node_chain.pending_transactions, 
        previous_hash=previous_hash
    )
    new_block.mine_block(node_chain.difficulty)
    
    node_chain.chain.append(new_block)
    node_chain.pending_transactions = []
    
    return jsonify({
        "message": "Block successfully mined and appended to the chain.",
        "block_hash": new_block.hash
    }), 200

@app.route('/register', methods=['POST'])
def register_nodes():
    incoming_data = request.get_json()
    nodes = incoming_data.get('nodes')

    if nodes is None:
        return jsonify({"error": "Please supply a valid list of nodes."}), 400

    for node in nodes:
        node_chain.nodes.add(node)

    return jsonify({
        "message": "Nodes successfully registered to the network.",
        "total_nodes": list(node_chain.nodes)
    }), 201

@app.route('/sync', methods=['GET'])
def consensus():
    longest_chain = None
    current_max_length = len(node_chain.chain)

    for node in node_chain.nodes:
        try:
            response = requests.get(f"{node}/block")
            if response.status_code == 200:
                length = response.json()['length']
                chain_data = response.json()['chain']

                if length > current_max_length:
                    current_max_length = length
                    longest_chain = chain_data
        except requests.exceptions.RequestException:
            continue

    if longest_chain:
        new_chain_objects = []
        for b_data in longest_chain:
            rebuilt_block = Block(b_data['index'], b_data['transactions'], b_data['previous_hash'])
            rebuilt_block.timestamp = b_data['timestamp']
            rebuilt_block.nonce = b_data['nonce']
            rebuilt_block.hash = b_data['hash']
            new_chain_objects.append(rebuilt_block)

        node_chain.chain = new_chain_objects

        return jsonify({
            "message": "Local chain replaced with the longest network chain.", 
            "new_chain": longest_chain
        }), 200
    
    return jsonify({
        "message": "Local chain is currently the authoritative longest chain."
    }), 200

if __name__ == "__main__":
    print(f"[{args.name}]'s Node is booting up on port {args.port}...")
    app.run(host='127.0.0.1', port=args.port, debug=True)