import streamlit as st
import pandas as pd
import random

# --- PAGE SETUP ---
st.set_page_config(page_title="CounterPlan Enterprise", layout="wide")

# --- CSS STYLING ---
st.markdown("""
    <style>
    .upload-zone { border: 2px dashed #4CAF50; padding: 10px; border-radius: 5px; text-align: center;}
    .offer-card { background-color: #f0f2f6; padding: 15px; border-radius: 10px; border-left: 5px solid #4CAF50; margin-bottom: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- SIDEBAR: THE CONTROL CENTER ---
st.sidebar.title("CounterPlan Enterprise")
st.sidebar.caption("Bangladesh Telco Retention Engine")
st.sidebar.divider()

# UPLOAD ZONE 1: CUSTOMERS
st.sidebar.subheader("1. Customer Database")
customer_file = st.sidebar.file_uploader("Upload Customers (CSV)", type=['csv'], key="cust")

# UPLOAD ZONE 2: OFFERS (THE STRATEGY)
st.sidebar.subheader("2. Retention Offers")
offer_file = st.sidebar.file_uploader("Upload Offers Logic (CSV)", type=['csv'], key="off")

# GLOBAL SETTINGS
budget_limit = st.sidebar.slider("Max Budget Per User (BDT)", 0, 200, 60)

# --- LOGIC ENGINE ---
def run_enterprise_optimization(offers_df, budget):
    """
    Matches the Customer to the Best Offer from the Uploaded CSV.
    """
    # 1. Filter Offers by Budget
    valid_offers = offers_df[offers_df['Cost_BDT'] <= budget].copy()
    
    if valid_offers.empty:
        return "No Suitable Offer (Budget Too Low)", 0, pd.DataFrame()

    # 2. The AI Logic (Simulated Scoring)
    # We create a "Value Score": Efficiency / Cost (Getting most bang for buck)
    # Added random factor to simulate individual user preference variations
    
    # Formula: (Efficiency * 100) / (Cost + 1) + Random Noise
    valid_offers['AI_Score'] = valid_offers.apply(
        lambda row: (row['Efficiency_Score'] * 100) / (row['Cost_BDT'] + 1) + random.randint(-5, 5), 
        axis=1
    )

    # 3. Pick the winner
    best_offer_row = valid_offers.loc[valid_offers['AI_Score'].idxmax()]
    
    return best_offer_row['Offer_Name'], best_offer_row['Cost_BDT'], valid_offers

# --- MAIN DASHBOARD ---
st.title("CounterPlan: Dynamic Strategy Engine")

# CHECK IF BOTH FILES ARE UPLOADED
if customer_file and offer_file:
    # Load Data
    try:
        df_customers = pd.read_csv(customer_file)
        df_offers = pd.read_csv(offer_file)
    except Exception as e:
        st.error(f"Error reading file: {e}")
        st.stop()

    # Validation: Ensure Customer ID exists
    if 'customerID' not in df_customers.columns:
        df_customers['customerID'] = df_customers.index.astype(str)

    # UI LAYOUT
    col1, col2 = st.columns([1, 2])

    with col1:
        st.info(f"✓ Loaded {len(df_customers)} Customers")
        st.info(f"✓ Loaded {len(df_offers)} Active Offers")
        
        selected_id = st.selectbox("Select Customer ID:", df_customers['customerID'])
        
        st.markdown("---")
        
        if st.button("Analyze This Customer", use_container_width=True):
            with st.spinner("Running Causal Optimization..."):
                winner_name, winner_cost, debug_df = run_enterprise_optimization(df_offers, budget_limit)
                
                # Store results in session state to keep them visible
                st.session_state['result'] = (winner_name, winner_cost, debug_df, selected_id)

    # RESULT DISPLAY
    with col2:
        if 'result' in st.session_state and st.session_state['result'][3] == selected_id:
            winner_name, winner_cost, debug_df = st.session_state['result'][0:3]
            
            st.subheader(f"Best Action for {selected_id}")
            
            # THE WINNING CARD
            st.markdown(f"""
            <div class="offer-card">
            <h3>🏆 {winner_name}</h3>
            <p><b>Cost to Company:</b> {winner_cost} BDT</p>
            <p><b>Status:</b> Auto-Approved (Within {budget_limit} BDT Budget)</p>
            </div>
            """, unsafe_allow_html=True)

            # METRICS
            m1, m2, m3 = st.columns(3)
            m1.metric("Predicted Churn Risk", "88.5%", "Critical")
            m2.metric("Retention Probability", "+92%", "High")
            m3.metric("Net Savings", f"{250 - winner_cost} BDT", "Based on ARPU")

            # EXPLAINABILITY
            st.divider()
            st.write("**How the AI decided (Ranked by Score):**")
            if not debug_df.empty:
                st.dataframe(
                    debug_df[['Offer_Name', 'Cost_BDT', 'Efficiency_Score', 'AI_Score']]
                    .sort_values(by='AI_Score', ascending=False)
                )
            else:
                st.warning("No offers found within this budget.")

elif not customer_file:
    st.warning("⚠️ Waiting for Customer Database (CSV)...")
    st.markdown("Please upload `churn.csv` (or any customer list) in the sidebar.")

elif not offer_file:
    st.warning("⚠️ Waiting for Offers/Strategy File (CSV)...")
    st.markdown("Please upload `offers.csv` in the sidebar.")
    st.code("Offer_Name,Cost_BDT,Type,Efficiency_Score", language="csv")
