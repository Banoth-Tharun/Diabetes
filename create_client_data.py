"""
Helper script to create client data files from the main dataset
Run this before starting federated learning clients
"""
import pandas as pd
import os
from pathlib import Path

def create_client_data_files(num_clients: int = 3, main_data: str = "data/pima_sample.csv"):
    """
    Split the main dataset into client-specific files
    
    Args:
        num_clients: Number of clients to create data for
        main_data: Path to main dataset CSV file
    """
    base_dir = Path(__file__).parent
    data_dir = base_dir / "data"
    main_data_path = base_dir / main_data
    
    # Check if main data file exists
    if not main_data_path.exists():
        print(f"Error: Main data file not found: {main_data_path}")
        print("Please ensure data/pima_sample.csv exists")
        return False
    
    # Load main dataset
    print(f"Loading data from {main_data_path}...")
    df = pd.read_csv(main_data_path)
    print(f"Total records: {len(df)}")
    
    # Check for required columns
    required_features = [
        'Pregnancies', 'Glucose', 'BloodPressure', 'SkinThickness', 'Insulin',
        'BMI', 'DiabetesPedigreeFunction', 'Age'
    ]
    
    missing_cols = [col for col in required_features if col not in df.columns]
    if missing_cols:
        print(f"Warning: Missing columns: {missing_cols}")
        print("Available columns:", list(df.columns))
    
    # Split data across clients
    chunk_size = len(df) // num_clients
    created_files = []
    
    for i in range(1, num_clients + 1):
        start_idx = (i - 1) * chunk_size
        end_idx = start_idx + chunk_size if i < num_clients else len(df)
        client_df = df.iloc[start_idx:end_idx]
        
        # Save client data file
        client_file = data_dir / f"pima_client_{i}.csv"
        client_df.to_csv(client_file, index=False)
        created_files.append(client_file)
        print(f"Created {client_file}: {len(client_df)} records (rows {start_idx} to {end_idx-1})")
    
    print(f"\n✓ Successfully created {num_clients} client data files")
    print(f"Files created in: {data_dir}")
    return True


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create client data files for federated learning")
    parser.add_argument("--clients", type=int, default=3, help="Number of clients (default: 3)")
    parser.add_argument("--data", type=str, default="data/pima_sample.csv", help="Main data file path")
    args = parser.parse_args()
    
    print("="*60)
    print("Creating Client Data Files for Federated Learning")
    print("="*60)
    print(f"Number of clients: {args.clients}")
    print(f"Main data file: {args.data}")
    print("="*60)
    print()
    
    success = create_client_data_files(args.clients, args.data)
    
    if success:
        print("\n" + "="*60)
        print("Next steps:")
        print("1. Start the server: python federated/server.py")
        print("2. Start clients in separate terminals:")
        for i in range(1, args.clients + 1):
            print(f"   python federated/client.py --data data/pima_client_{i}.csv --client-id client_{i}")
        print("="*60)
    else:
        print("\nFailed to create client data files. Please check the error messages above.")

