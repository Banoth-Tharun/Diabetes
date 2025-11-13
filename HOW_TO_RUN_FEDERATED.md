# How to Run Federated Learning

This guide explains how to run the federated learning system for the Diabetes Management application.

## Prerequisites

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   
   Make sure `flwr==1.8.0` is installed (already in requirements.txt)

2. **Data File**
   - Ensure `data/pima_sample.csv` exists
   - The simulation script will automatically split this into client datasets

## Method 1: Quick Simulation (Recommended for Testing)

This is the easiest way to test federated learning. It automatically:
- Splits data into client datasets
- Starts the server
- Starts multiple clients
- Runs the full training process

### Run the Simulation:

```bash
python federated_sim.py --rounds 10 --clients 3
```

**Parameters:**
- `--rounds`: Number of federated learning rounds (default: 5)
- `--clients`: Number of clients to simulate (default: 3)

**Example:**
```bash
# Run with 10 rounds and 3 clients
python federated_sim.py --rounds 10 --clients 3

# Run with 5 rounds and 2 clients (faster)
python federated_sim.py --rounds 5 --clients 2
```

**What happens:**
1. Creates client data files (`data/pima_client_1.csv`, `pima_client_2.csv`, etc.)
2. Starts the federated learning server
3. Connects multiple clients
4. Trains the model across multiple rounds
5. Saves the model to `ml/federated_model.pkl`

**Expected Output:**
```
============================================================
Federated Learning Simulation
============================================================
Rounds: 10
Clients: 3
============================================================

Created client data file: data/pima_client_1.csv
Created client data file: data/pima_client_2.csv
Created client data file: data/pima_client_3.csv

Starting Federated Learning Server...
Starting Client 1...
Starting Client 2...
Starting Client 3...

All clients connected. Training in progress...
(This may take a few minutes)

[Training logs...]

============================================================
Federated Learning Complete!
============================================================
Model saved to: ml/federated_model.pkl
You can now use this model in the Flask application.
```

## Method 2: Manual Setup (For Production)

For a more controlled setup, run server and clients separately:

### Step 1: Start the Server

Open Terminal 1:
```bash
python federated/server.py
```

You should see:
```
Starting Federated Learning Server...
Waiting for clients to connect...
Server will run for 10 rounds
Server address: 0.0.0.0:8080
```

### Step 2: Start Clients

Open separate terminals for each client:

**Terminal 2 - Client 1:**
```bash
python federated/client.py --data data/pima_client_1.csv --client-id client_1 --server localhost:8080
```

**Terminal 3 - Client 2:**
```bash
python federated/client.py --data data/pima_client_2.csv --client-id client_2 --server localhost:8080
```

**Terminal 4 - Client 3:**
```bash
python federated/client.py --data data/pima_client_3.csv --client-id client_3 --server localhost:8080
```

**Note:** If client data files don't exist, create them first:
```bash
# Split the main dataset (run once)
python -c "
import pandas as pd
df = pd.read_csv('data/pima_sample.csv')
n = 3
chunk = len(df) // n
for i in range(n):
    start = i * chunk
    end = start + chunk if i < n-1 else len(df)
    df.iloc[start:end].to_csv(f'data/pima_client_{i+1}.csv', index=False)
    print(f'Created data/pima_client_{i+1}.csv')
"
```

## After Training

### Check if Model was Created

```bash
# Check if model file exists
ls ml/federated_model.pkl
```

### Use in Flask Application

The Flask app will automatically use the federated model if it exists:

1. **Start Flask app:**
   ```bash
   python app.py
   ```

2. **Make predictions:**
   - The app automatically detects `ml/federated_model.pkl`
   - If found, uses federated model
   - Otherwise, falls back to regular model

3. **Verify model in use:**
   - Check console output when making predictions
   - Should see: "Loaded federated model from ml/federated_model.pkl"

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'flwr'"

**Solution:**
```bash
pip install flwr==1.8.0
```

### Issue: "FileNotFoundError: data/pima_sample.csv"

**Solution:**
- Ensure the data file exists in the `data/` directory
- Or provide your own CSV file with the required columns

### Issue: "Address already in use" (Port 8080)

**Solution:**
- Change the port in `federated/server.py`:
  ```python
  fl.server.start_server(server_address="0.0.0.0:8081", ...)
  ```
- Update client connections to use the new port

### Issue: Clients not connecting

**Solution:**
- Make sure server is running first
- Check that server address matches in client commands
- Verify firewall isn't blocking port 8080

### Issue: "Minimum clients not available"

**Solution:**
- Ensure at least 2 clients are connected
- Check `min_fit_clients=2` in server configuration
- Wait for all clients to connect before training starts

## Configuration Options

### Server Configuration (`federated/server.py`)

Edit these parameters:
```python
fraction_fit=0.3,      # Use 30% of clients per round
min_fit_clients=2,      # Minimum clients needed
num_rounds=10,          # Number of training rounds
```

### Client Configuration (`federated/client.py`)

Edit these parameters:
```python
local_epochs=5,         # Training epochs per client
```

## Expected Training Time

- **3 clients, 10 rounds**: ~2-5 minutes
- **5 clients, 20 rounds**: ~5-10 minutes
- Depends on data size and system performance

## Next Steps

1. ✅ Run simulation: `python federated_sim.py --rounds 10 --clients 3`
2. ✅ Verify model: Check `ml/federated_model.pkl` exists
3. ✅ Test in Flask: Start app and make predictions
4. ✅ Check logs: Verify federated model is being used

## Production Deployment

For production:
- Use proper authentication between server and clients
- Implement encryption for parameter transmission
- Add differential privacy for additional security
- Use secure communication (HTTPS/TLS)
- Monitor training metrics and model performance

