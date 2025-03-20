####Sport Matrix------------------------------------------------------------------------------------Backend Code
# Import necessary libraries
from flask import Flask, render_template, request, redirect, jsonify
import openpyxl
import os
import pandas as pd
import numpy as np
from sklearn.tree import DecisionTreeRegressor
import matplotlib
matplotlib.use('Agg')  # Fix for Flask server
import matplotlib.pyplot as plt
import io
import base64
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
####----------------------------------------------------------------------------------------------------------------
#### Sport Matrix excel datbase code
# Get the absolute path to the current directory and create the Excel file there
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
EXCEL_FILE = os.path.join(BASE_DIR, 'data.xlsx')

app = Flask(__name__)

# Function to create the Excel file if it doesn't exist
def create_excel_file():
    if not os.path.exists(EXCEL_FILE):
        wb = openpyxl.Workbook()
        ws = wb.active
        # Create headers (you can modify these based on your form fields)
        ws.append(["Form Type", "Name", "Age", "Height", "Weight", "Passing", "Shooting", "Dribbling", "Pace", "Physical", "Defending"])
        wb.save(EXCEL_FILE)
####----------------------------------------------------------------------------------------------------------------        
#Team Lineup
EXCEL_FILE = "data.xlsx"

# Hybrid Ranking Functions (TOPSIS + Decision Tree)
def preprocess_data(df):
    """Compute BMI and average player stats."""
    df = df.copy()
    df["Height_m"] = df["Height"] / 100
    df["BMI"] = df["Weight"] / (df["Height_m"] ** 2)
    df["Performance Score"] = df[["Passing", "Shooting", "Dribbling", "Pace", "Physical", "Defending"]].mean(axis=1)
    
    grouped = df.groupby(["Name", "Form Type"])[["BMI", "Performance Score", "Passing", "Shooting", "Dribbling", "Pace", "Physical", "Defending"]].mean().reset_index()
    return grouped

def normalize(df, columns):
    """Min-Max Normalization."""
    df_norm = df.copy()
    for col in columns:
        col_min, col_max = df[col].min(), df[col].max()
        df_norm[col] = (df[col] - col_min) / (col_max - col_min) if col_min != col_max else 0.5
    return df_norm

def topsis_ranking(df):
    """Apply TOPSIS ranking method to player attributes."""
    criteria_columns = ["BMI", "Performance Score", "Passing", "Shooting", "Dribbling", "Pace", "Physical", "Defending"]
    # Ensure "Form Type" is NOT included in calculations
    df_numeric = df[criteria_columns].copy()

    #  Debugging Print: Check Available Columns
    print("Columns in DataFrame for TOPSIS:", df.columns)
    print("Expected Criteria Columns:", criteria_columns)


    # Check Shape Before Applying Weights
    print("Shape of DataFrame:", df_numeric.shape, "Length of Weights:", len(criteria_columns))

    # Normalize data
    df_normalized = normalize(df_numeric, criteria_columns)

    #  Adjust Weight Array to Match Feature Count
    weights = np.array([0.1, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.05])  
    if len(weights) != len(criteria_columns):
        raise ValueError(f"Shape mismatch: DataFrame has {df_numeric.shape[1]} columns but weights have {len(weights)} values.")

    # Weighted normalized matrix
    df_weighted = df_normalized * weights

    # Compute TOPSIS Score
    ideal_best = df_weighted.max()
    ideal_worst = df_weighted.min()

    dist_best = np.sqrt(((df_weighted - ideal_best) ** 2).sum(axis=1))
    dist_worst = np.sqrt(((df_weighted - ideal_worst) ** 2).sum(axis=1))

    df["TOPSIS_Score"] = dist_worst / (dist_best + dist_worst)
    df["Rank"] = df["TOPSIS_Score"].rank(ascending=False)

    return df.sort_values(by="Rank")


def train_decision_tree(df):
    """Train Decision Tree Regressor to predict Selection Score."""
    features = ["BMI", "Performance Score", "Passing", "Shooting", "Dribbling", "Pace", "Physical", "Defending"]
    
    # Fix: Fill Missing Values Only in Numeric Columns
    df[features] = df[features].apply(lambda x: x.fillna(x.mean()))
    X = df[features]
    y = df["Performance Score"]
    
    # Split Data: 80% Training, 20% Testing
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
    model = DecisionTreeRegressor(random_state=42)
    model.fit(X_train, y_train)
    
    df["Selection_Score"] = model.predict(X)
    
    #  Calculate & Print Accuracy (Mean Absolute Error)
    y_pred = model.predict(X_test)
    mae = mean_absolute_error(y_test, y_pred)
    accuracy = 100 - mae  # Lower MAE is better
    
    print(f" Model Accuracy (Lower MAE is better): {accuracy:.2f}%")
    return df

def compute_hybrid_score(df):
    """Compute Hybrid Score combining TOPSIS & Decision Tree Scores."""
    df["Hybrid Score"] = (0.5 * df["TOPSIS_Score"] * 100) + (0.5 * df["Selection_Score"])
    df["Final Rank"] = df["Hybrid Score"].rank(ascending=False)
    return df.sort_values(by="Final Rank")

def get_top_players(df):
    """Retrieve top players for each form type."""
    return {
        "ATC": df[df["Form Type"] == "ATC"].nlargest(3, "Hybrid Score"),
        "MID": df[df["Form Type"] == "MID"].nlargest(3, "Hybrid Score"),
        "DEF": df[df["Form Type"] == "DEF"].nlargest(4, "Hybrid Score"),
        "GK": df[df["Form Type"] == "GK"].nlargest(2, "Hybrid Score")
    }

####----------------------------------------------------------------------------------------------------------------
# Route to delete all records while keeping headers
@app.route('/delete-records', methods=['POST'])
def delete_records():
    try:
        # Load existing data
        df = pd.read_excel(EXCEL_FILE)
        
        # Clear all data but retain headers
        df.iloc[0:0].to_excel(EXCEL_FILE, index=False)
        
        return jsonify({"message": "All records deleted successfully!"})
    except Exception as e:
        return jsonify({"error": str(e)})
####----------------------------------------------------------------------------------------------------------------
# Route to render ATC form
@app.route('/atc')
def atc_form():
    return render_template('sportmatrixATC.html')

# Route to render MID form
@app.route('/mid')
def mid_form():
    return render_template('sportmatrixMID.html')

# Home route
@app.route('/')
def home():
    return render_template('sportmatrix1.html')

# Add player route
@app.route('/addplayer')
def addplayer():
    return render_template('sportmatrix2.html')

# Route to render DEF form
@app.route('/def')
def def_form():
    return render_template('sportmatrixDEF.html')

# Route to render GK form
@app.route('/gk')
def gk_form():
    return render_template('sportmatrixGK.html')
####----------------------------------------------------------------------------------------------------------------
# Route to render Team lineup form
# Hybrid Rankings and scater plot
@app.route('/Teamlineup')
def team_analysis():
    """Compute Hybrid Rankings & Pass Scatter Plot Data to HTML."""
    try:
        df = pd.read_excel(EXCEL_FILE)
        if df.empty:
            return render_template("sportmatrixTEAM.html", rankings=None, plot_url=None)

        # Step 1: Process Data
        df_processed = preprocess_data(df)
        df_ranked = topsis_ranking(df_processed)
        df_with_ml = train_decision_tree(df_ranked)
        df_final = compute_hybrid_score(df_with_ml)

        # Step 2: Get Only Top 12 Players
        top_players = get_top_players(df_final)
        df_top = pd.concat(top_players.values())  # Convert dictionary to DataFrame

        # Step 3: Generate Scatter Plot (Only for Top 12 Players)
        plt.figure(figsize=(10, 6))
        scatter = plt.scatter(
            df_top["Selection_Score"],  # X-Axis
            df_top["TOPSIS_Score"],     # Y-Axis
            c=df_top["Hybrid Score"],   # Color based on Hybrid Score
            cmap="coolwarm",            # Color theme
            edgecolors="black",
            s=100,                      # Larger point size for better visibility
            alpha=0.8
        )

        # Add Colorbar (Hybrid Score)
        plt.colorbar(scatter, label="Selection Score (Hybrid)")
        plt.xlabel("Potential Score (Predicted)")
        plt.ylabel("Performance Score (TOPSIS)")
        plt.title("Selection Score Visualization (Top 12 Players)")
        plt.grid(True)

        #  Move Player Legend Below Graph**
        import matplotlib.patches as mpatches
        legend_patches = [
            mpatches.Patch(color=scatter.to_rgba(score), label=name)
            for name, score in zip(df_top["Name"], df_top["Hybrid Score"])
        ]

        plt.legend(
            handles=legend_patches,
            title="Players",
            loc="upper center",
            bbox_to_anchor=(0.5, -0.15),  # Moves legend **below the graph**
            borderaxespad=0,
            ncol=3  # Arranges legend items in 3 columns for better spacing
        )

        # Convert plot to base64
        img = io.BytesIO()
        plt.savefig(img, format="png", bbox_inches="tight")
        img.seek(0)
        plot_url = base64.b64encode(img.getvalue()).decode()

        return render_template("sportmatrixTEAM.html", rankings=top_players, plot_url=plot_url)

    except Exception as e:
        return str(e)
####----------------------------------------------------------------------------------------------------------------
# Route to handle form submission
@app.route('/submit', methods=['POST'])
def submit():
    form_type = request.form['form_type']  # Get form type from hidden input
    
    # Collect common form fields
    name = request.form['name']
    age = int(request.form['age'])
    height = float(request.form['height'])
    weight = float(request.form['weight'])
    passing = int(request.form['passing'])
    shooting = int(request.form['shooting'])
    dribbling = int(request.form['dribbling'])
    pace = int(request.form['pace'])
    physical = int(request.form['physical'])
    defending = int(request.form['defending'])
    
    # Ensure Excel file exists
    create_excel_file()

    # Open the Excel file and append the data
    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append([form_type, name, age, height, weight, passing, shooting, dribbling, pace, physical, defending])
    wb.save(EXCEL_FILE)
    
    return redirect('/matrix')
####----------------------------------------------------------------------------------------------------------------
# Thank you page after form submission
@app.route('/matrix')
def thankyou():
    df = pd.read_excel(EXCEL_FILE)
    if not df.empty:
        latest_entry = df.iloc[-1].to_dict()  # Convert the latest row to a dictionary
    else:
        latest_entry = None

    # Define thresholds for form types (ATC, MID, DEF, etc.)
    thresholds = {
        'ATC': {'Passing': 85, 'Shooting': 95, 'Dribbling': 95, 'Pace': 90, 'Physical': 50, 'Defending': 40},
        'MID': {'Passing': 90, 'Shooting': 85, 'Dribbling': 80, 'Pace': 75, 'Physical': 50, 'Defending': 70},
        'DEF': {'Passing': 75, 'Shooting': 60, 'Dribbling': 70, 'Pace': 85, 'Physical': 75, 'Defending': 95},
        'GK': {'Passing': 70, 'Shooting': 80, 'Dribbling': 45, 'Pace': 50, 'Physical': 75, 'Defending': 95}
        # Add more form types if necessary
    }

    if latest_entry:
        # Define player stats from the latest entry
        player_stats = {
            'Passing': latest_entry['Passing'],
            'Shooting': latest_entry['Shooting'],
            'Dribbling': latest_entry['Dribbling'],
            'Pace': latest_entry['Pace'],
            'Physical': latest_entry['Physical'],
            'Defending': latest_entry['Defending']
        }
        
        # Extract form type for analysis
        form_type = latest_entry['Form Type']
        threshold_values = thresholds.get(form_type, {})  # Get the corresponding thresholds

        # Perform the analysis by comparing player stats with the thresholds
        analysis = {}
        for key in player_stats:
            analysis[key] = 'good' if player_stats[key] >= thresholds[form_type][key] else 'low'
        
        # Render the final result template with player data, analysis, and thresholds
        return render_template('sportmatrixFIN.html', player=latest_entry, analysis=analysis, thresholds=threshold_values)
    else:
        # Handle case when no data is available
        return render_template('sportmatrixFIN.html', player=None, analysis=None, thresholds={})

if __name__ == '__main__':
    app.run(debug=True)
####-------------------------------------------------------------------------------------------------------------------
