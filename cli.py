import requests
import argparse
import json

def get_url(port):
    return f"http://127.0.0.1:{port}"

def print_response(response):
    try:
        print(json.dumps(response.json(), indent=2))
    except:
        print(response.text)

def main():
    parser = argparse.ArgumentParser(description="Blockchain CLI Client")
    parser.add_argument('command', choices=['profile', 'chain', 'register', 'send', 'mempool', 'mine', 'sync'], 
                        help='The action you want to perform')
    parser.add_argument('-p', '--port', type=int, default=5000, 
                        help='Port of the node you are talking to (default: 5000)')
    
    # Optional arguments for specific commands
    parser.add_argument('--node', type=str, help='Target node URL (used with "register")')
    parser.add_argument('--receiver', type=str, help='Receiver public key (used with "send")')
    parser.add_argument('--amount', type=float, help='Amount to send (used with "send")')

    args = parser.parse_args()
    base_url = get_url(args.port)

    try:
        if args.command == 'profile':
            print_response(requests.get(f"{base_url}/profile"))
            
        elif args.command == 'chain':
            print_response(requests.get(f"{base_url}/block"))

        elif args.command == 'register':
            if not args.node:
                print("❌ Error: Please provide --node URL (e.g., --node http://127.0.0.1:5001)")
                return
            print_response(requests.post(f"{base_url}/register", json={"nodes": [args.node]}))

        elif args.command == 'send':
            if not args.receiver or not args.amount:
                print("❌ Error: Please provide --receiver and --amount")
                return
            # We handle the newline characters in the pasted PEM key
            receiver_key = args.receiver.replace('\\n', '\n')
            print_response(requests.post(f"{base_url}/transaction", json={"receiver": receiver_key, "amount": args.amount}))

        elif args.command == 'mempool':
            print_response(requests.get(f"{base_url}/mempool"))

        elif args.command == 'mine':
            print_response(requests.get(f"{base_url}/mine"))

        elif args.command == 'sync':
            print_response(requests.get(f"{base_url}/sync"))

    except requests.exceptions.ConnectionError:
        print(f"❌ Error: Could not connect to node on port {args.port}. Is it running?")

if __name__ == "__main__":
    main()