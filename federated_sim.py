"""
Federated Learning Simulation
Simulates federated training with multiple clients using local data
"""
import os
import subprocess
import sys
import time
import argparse
from pathlib import Path

def simulate_federated_learning(rounds: int = 5, num_clients: int = 3):
    """
    Simulate federated learning with multiple clients
    
    Args:
        rounds: Number of federated learning rounds
        num_clients: Number of client processes to simulate
    """
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data"
    server_script = base_dir / "federated" / "server.py"
    client_script = base_dir / "federated" / "client.py"
    
    # Check if data files exist
    data_files = []
    for i in range(1, num_clients + 1):
        data_file = data_dir / f"pima_client_{i}.csv"
        if not data_file.exists():
            # Create sample data file by splitting the main dataset
            main_data = data_dir / "pima_sample.csv"
            if main_data.exists():
                import pandas as pd
                df = pd.read_csv(main_data)
                # Split data across clients
                chunk_size = len(df) // num_clients
                start_idx = (i - 1) * chunk_size
                end_idx = start_idx + chunk_size if i < num_clients else len(df)
                client_df = df.iloc[start_idx:end_idx]
                client_df.to_csv(data_file, index=False)
                print(f"Created client data file: {data_file}")
        data_files.append(data_file)
    
    print(f"\n{'='*60}")
    print("Federated Learning Simulation")
    print(f"{'='*60}")
    print(f"Rounds: {rounds}")
    print(f"Clients: {num_clients}")
    print(f"{'='*60}\n")
    
    # Start server in background
    print("Starting Federated Learning Server...")
    server_process = subprocess.Popen(
        [sys.executable, str(server_script)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(3)
    
    # Start clients
    client_processes = []
    for i, data_file in enumerate(data_files, 1):
        print(f"Starting Client {i}...")
        client_process = subprocess.Popen(
            [
                sys.executable, str(client_script),
                "--data", str(data_file),
                "--client-id", f"client_{i}",
                "--server", "localhost:8080"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        client_processes.append(client_process)
        time.sleep(1)  # Stagger client starts
    
    print("\nAll clients connected. Training in progress...")
    print("(This may take a few minutes)\n")
    
    # Wait for all processes to complete
    try:
        server_process.wait(timeout=300)  # 5 minute timeout
        for client_process in client_processes:
            client_process.wait(timeout=60)
        
        print("\n" + "="*60)
        print("Federated Learning Complete!")
        print("="*60)
        print(f"Model saved to: ml/federated_model.pkl")
        print("You can now use this model in the Flask application.")
        
    except subprocess.TimeoutExpired:
        print("\nWarning: Process timeout. Some clients may still be running.")
        server_process.terminate()
        for client_process in client_processes:
            client_process.terminate()
    
    except KeyboardInterrupt:
        print("\n\nStopping federated learning...")
        server_process.terminate()
        for client_process in client_processes:
            client_process.terminate()
        print("Stopped.")


def main():
    parser = argparse.ArgumentParser(description="Federated Learning Simulation")
    parser.add_argument("--rounds", type=int, default=5, help="Number of federated rounds")
    parser.add_argument("--clients", type=int, default=3, help="Number of clients")
    args = parser.parse_args()
    
    simulate_federated_learning(rounds=args.rounds, num_clients=args.clients)


if __name__ == "__main__":
    main()
