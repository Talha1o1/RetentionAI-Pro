import streamlit as st
import pandas as pd
import random
from fpdf import FPDF

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="RetentionAI Pro", layout="wide")

# --- VISUAL STYLING (FIXED) ---
st.markdown("""
    <style>
    .risk-high { color: #dc3545; font-weight: bold; }
    .risk-low { color: #28a745; font-weight: bold; }
    
    /* THE FIX: Force text to be BLACK inside the white box */
    .offer-box { 
        background-color: #f8f9fa; 
        color: #000000; 
        border-left: 5px solid #007bff; 
        padding: 15px; 
        border-radius: 5px; 
    }
    
    /* Ensure headers inside the box are also black */
    .offer-box h4, .offer-box p, .offer-box i {
        color: #000000 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- INTELLIGENCE ENGINE ---
def analyze_customer_risk(row):
    """
    Analyzes specific customer data to calculate risk and generate reasons.
    """
    risk_score = 50  # Base risk
    reasons = []
    pdf_reasons = [] # Safe version for PDF

    # 1. Analyze Tenure (Loyalty)
    if row['tenure'] < 6:
        risk_score += 30
        reasons.append("⚠️ New Customer (High Instability)")
        pdf_reasons.append("[!] New Customer (High Instability)")
    elif row['tenure'] > 60:
        risk_score -= 20
        reasons.append("✅ Loyal Long-term User")
        pdf_reasons.append("[+] Loyal Long-term User")

    # 2. Analyze Bill (Price Sensitivity)
    if row['MonthlyCharges'] > 80:
        risk_score += 20
        reasons.append("⚠️ High Monthly Expense (Price Sensitive)")
        pdf_reasons.append("[!] High Monthly Expense (Price Sensitive)")
    elif row['MonthlyCharges'] < 30:
        risk_score -= 10
        reasons.append("✅ Low Bill Burden")
        pdf_reasons.append("[+] Low Bill Burden")

    # 3. Analyze Contract (Commitment)
    if 'Month-to-month' in str(row['Contract']):
        risk_score += 15
        reasons.append("⚠️ No Long-term Contract")
        pdf_reasons.append("[!] No Long-term Contract")
    
    # Cap risk between 1% and 99%
    final_risk = max(1, min(99, risk_score))
    return final_risk, reasons, pdf_reasons

def find_best_offer(offers_df, budget, risk_reasons):
    """
    Selects the best offer based on the specific 'Why' (Reasons).
    """
    # 1. Filter by Budget
    valid_offers = offers_df[offers_df['Cost_BDT'] <= budget].copy()
    
    if valid_offers.empty:
        return None, "Budget too low for any offer."

    # 2. Strategy Matching Logic
    prioritize_type = "Standard"
    reasons_str = str(risk_reasons)
    
    if "Price Sensitive" in reasons_str:
        prioritize_type = "Financial"
    elif "Instability" in reasons_str:
        prioritize_type = "Data"

    # 3. Score the offers
    def score_offer(row):
        score = row['Efficiency_Score'] * 100
        if row['Type'] == prioritize_type:
            score += 25 
        return score

    valid_offers['Match_Score'] = valid_offers.apply(score_offer, axis=1)
    
    # Pick the winner
    best_offer = valid_offers.loc[valid_offers['Match_Score'].idxmax()]
    
    explanation = f"Selected because customer shows '{prioritize_type}' signals. " \
                  f"This offer provides the highest efficiency ({best_offer['Efficiency_Score']}) " \
                  f"within the {budget} BDT budget."
                  
    return best_offer, explanation

# --- PDF GENERATOR ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 16)
        self.cell(0, 10, 'RetentionAI - Strategic Analysis', 0, 1, 'C')
        self.ln(10)

    def add_section(self, title, body):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(230, 230, 230)
        self.cell(0, 8, title, 0, 1, 'L', 1)
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 6, body)
        self.ln(5)

# --- APP LAYOUT ---
st.sidebar.title("⚙️ Control Panel")
st.sidebar.info("Upload your separate Data and Strategy files below.")

# Uploads
dataset = st.sidebar.file_uploader("1. Customer Data (CSV)", type=['csv'])
strategy = st.sidebar.file_uploader("2. Strategy/Offers (CSV)", type=['csv'])
budget_limit = st.sidebar.slider("Max Budget (BDT)", 0, 200, 50)

st.title("🚀 RetentionAI Enterprise")

if dataset and strategy:
    try:
        df = pd.read_csv(dataset)
        offers = pd.read_csv(strategy)
    except Exception as e:
        st.error(f"Error reading CSV files: {e}")
        st.stop()

    # Sidebar Selection
    if 'customerID' not in df.columns:
        df['customerID'] = df.index.astype(str)
        
    customer_ids = df['customerID'].tolist()
    
    # Selection
    selected_id = st.sidebar.selectbox("Select Customer to Analyze", customer_ids)
    
    # Get Customer Data
    customer_row = df[df['customerID'] == selected_id].iloc[0]

    # --- MAIN DASHBOARD ---
    col1, col2 = st.columns([1, 2])

    with col1:
        st.subheader("Customer Profile")
        st.write(f"**ID:** {selected_id}")
        st.write(f"**Tenure:** {customer_row['tenure']} months")
        st.write(f"**Monthly Bill:** {customer_row['MonthlyCharges']}")
        st.write(f"**Contract:** {customer_row['Contract']}")
        
        st.info("👆 Change Customer in Sidebar to update.")

    # ANALYSIS RESULT
    with col2:
        st.subheader("AI Diagnosis & Prescription")
        
        # 1. CALCULATE RISK
        risk, reasons, pdf_reasons = analyze_customer_risk(customer_row)
        
        risk_color = "red" if risk > 50 else "green"
        st.markdown(f"### Churn Probability: <span style='color:{risk_color}'>{risk}%</span>", unsafe_allow_html=True)
        
        with st.expander("Why this risk score? (Explainability)", expanded=True):
            for reason in reasons:
                st.write(f"- {reason}")

        # 2. FIND SOLUTION
        best_offer, match_logic = find_best_offer(offers, budget_limit, reasons)
        
        if best_offer is not None:
            # THIS BOX NOW HAS BLACK TEXT
            st.markdown(f"""
            <div class="offer-box">
                <h4>✨ Recommended Action: {best_offer['Offer_Name']}</h4>
                <p><b>Cost:</b> {best_offer['Cost_BDT']} BDT | <b>Type:</b> {best_offer['Type']}</p>
                <p><i>{match_logic}</i></p>
            </div>
            """, unsafe_allow_html=True)
            
            # 3. PDF REPORT (Safe Mode)
            pdf = PDFReport()
            pdf.add_page()
            
            risk_text = f"The system calculated a churn probability of {risk}% based on tenure and spending patterns.\n\nKey drivers:\n- " + "\n- ".join(pdf_reasons)
            pdf.add_section("1. Risk Assessment", risk_text)
            
            strat_text = f"Offer: {best_offer['Offer_Name']}\nType: {best_offer['Type']}\nCost: {best_offer['Cost_BDT']} BDT"
            pdf.add_section("2. Recommended Strategy", strat_text)
            
            pdf.add_section("3. Logic Explanation", match_logic)
            
            try:
                pdf_data = pdf.output(dest="S").encode("latin-1", errors='replace')
                st.download_button(
                    label="📄 Download Strategy Report", 
                    data=pdf_data, 
                    file_name=f"Report_{selected_id}.pdf", 
                    mime="application/pdf"
                )
            except Exception as e:
                st.error(f"PDF Generation Error: {e}")

        else:
            st.warning("⚠️ No offers available within this budget. Increase the slider!")

elif not dataset:
    st.info("👋 Welcome! Please upload `churn.csv` to begin.")
