=========================================================
BLOCKCHAIN TESTING COMMANDS (Save this as commands.txt)
=========================================================

---------------------------------------------------------
STEP 1: START THE NODES
(Open 3 separate terminal windows and run one command in each. Leave them running!)
---------------------------------------------------------
Terminal 1:  python node.py -n Node1 -p 5000
Terminal 2:  python node.py -n Node2 -p 5001
Terminal 3:  python node.py -n Node3 -p 5002

---------------------------------------------------------
STEP 2: CONNECT THE NETWORK (MESH SETUP)
(Open a 4th terminal to run all the cli.py commands below)
---------------------------------------------------------
# Tell Port 5000 about 5001 and 5002
python cli.py register -p 5000 --node http://127.0.0.1:5001
python cli.py register -p 5000 --node http://127.0.0.1:5002

# Tell Port 5001 about 5000 and 5002
python cli.py register -p 5001 --node http://127.0.0.1:5000
python cli.py register -p 5001 --node http://127.0.0.1:5002

# Tell Port 5002 about 5000 and 5001
python cli.py register -p 5002 --node http://127.0.0.1:5000
python cli.py register -p 5002 --node http://127.0.0.1:5001

---------------------------------------------------------
STEP 3: GET Node2'S PUBLIC KEY
---------------------------------------------------------
# Check Node2's profile to get his address
python cli.py profile -p 5001

*** IMPORTANT: Copy the ENTIRE "public_key" string from the output. ***

---------------------------------------------------------
STEP 4: SEND A TRANSACTION
---------------------------------------------------------
# Node1 (5000) sends 1 coin to Node2 (5001)
# Replace the text inside the quotes with the key you just copied.
python cli.py send -p 5000 --amount 1 --receiver "-----BEGIN PUBLIC KEY-----\n...YOUR_COPIED_KEY...\n-----END PUBLIC KEY-----\n"

# Verify it reached Node3's (5002) mempool automatically!
python cli.py mempool -p 5002

---------------------------------------------------------
STEP 5: MINE THE BLOCK
---------------------------------------------------------
# Let's let Node3 (5002) do the hard work and get the 7 coin reward.
python cli.py mine -p 5002

---------------------------------------------------------
STEP 6: SYNC THE NETWORK
---------------------------------------------------------
# Node3 has the longest chain now. Tell Node1 and Node2 to pull his data.
python cli.py sync -p 5000
python cli.py sync -p 5001

---------------------------------------------------------
STEP 7: VERIFY THE FINAL BALANCES
---------------------------------------------------------
# Node1 started with 3, sent 1. Should have 2.
python cli.py profile -p 5000

# Node2 started with 3, received 1. Should have 4.
python cli.py profile -p 5001

# Node3 started with 3, mined a block (+67). Should have 70.
python cli.py profile -p 5002

# Check the ledger to see the official history on any node:
python cli.py chain -p 5000