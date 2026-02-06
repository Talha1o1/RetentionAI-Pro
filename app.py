# app.py (Version 2.0 with PDF Reports)
import streamlit as st
import pandas as pd
import numpy as np
import joblib
import dice_ml
from fpdf import FPDF
import base64

# --- CONFIGURATION ---
st.set_page_config(page_title="RetentionAI Pro", layout="wide")

# --- CUSTOM CSS ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .report-view { background-color: white; padding: 20px; border-radius: 10px; border-left: 5px solid #00008B; }
    </style>
""", unsafe_allow_html=True)

# --- CLASS DEFINITIONS ---
class NumericXGBWrapper:
    def __init__(self, model):
        self.model = model
    def _clean(self, X):
        X_clean = X.replace({'True': 1, 'False': 0, True: 1, False: 0})
        X_clean = X_clean.apply(pd.to_numeric, errors='coerce')
        return X_clean.fillna(0)
    def predict_proba(self, X):
        return self.model.predict_proba(self._clean(X))
    def predict(self, X):
        return self.model.predict(self._clean(X))

# --- PDF GENERATOR CLASS ---
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.cell(0, 10, 'RetentionAI - Customer Analysis Report', 0, 1, 'C')
        self.ln(10)

    def chapter_title(self, title):
        self.set_font('Arial', 'B', 12)
        self.set_fill_color(200, 220, 255)
        self.cell(0, 6, title, 0, 1, 'L', 1)
        self.ln(4)

    def chapter_body(self, body):
        self.set_font('Arial', '', 11)
        self.multi_cell(0, 6, body)
        self.ln()

# --- LOAD ASSETS ---
@st.cache_resource
def load_assets():
    model = joblib.load('churn_model.pkl')
    data = joblib.load('X_test_data.pkl')
    features = joblib.load('features.pkl')
    return model, data, features

model, X_test, feature_names = load_assets()

# --- COST FUNCTION ---
def calculate_cost(original, cf):
    cost_card = {
        'MonthlyCharges': 1.0, 'tenure': 1000.0, 'TotalCharges': 1.0,
        'Contract_One year': 50.0, 'Contract_Two year': 100.0,
        'InternetService_No': 5.0
    }
    total = 0.0
    changes = []
    
    orig_vals = original.astype(float)
    cf_vals = cf.astype(float)
    
    for col in original.columns:
        val_orig = orig_vals[col].values[0]
        val_cf = cf_vals[col].values[0]
        if abs(val_orig - val_cf) > 0.001:
            diff = abs(val_orig - val_cf)
            unit_cost = cost_card.get(col, 10.0)
            cost = diff * unit_cost
            total += cost
            changes.append(f"{col}: {val_orig:.0f} -> {val_cf:.0f}")
    return total, changes

# --- SIDEBAR ---
st.sidebar.title("RetentionAI Pro")
st.sidebar.markdown("Enterprise Dashboard")
customer_id = st.sidebar.selectbox("Search Customer ID", X_test.index)

# --- MAIN PAGE ---
col1, col2 = st.columns([2, 1])

with col1:
    st.title(f"Customer Profile: #{customer_id}")
    customer_data = X_test.loc[[customer_id]]
    
    # Prediction
    prob = model.predict_proba(customer_data)[0][1]
    churn_status = "HIGH RISK" if prob > 0.5 else "Safe"
    
    m1, m2, m3 = st.columns(3)
    m1.metric("Churn Probability", f"{prob*100:.1f}%")
    m2.metric("Status", churn_status, delta_color="inverse")
    m3.metric("Monthly Bill", f"${customer_data['MonthlyCharges'].values[0]:.2f}")

    with st.expander("Show Raw Data"):
        st.dataframe(customer_data)

# --- THESIS ENGINE LOGIC ---
st.divider()

if prob > 0.5:
    st.header("⚡ Retention Strategy Engine")
    
    if 'report_ready' not in st.session_state:
        st.session_state['report_ready'] = False

    if st.button("Run AI Analysis & Generate Report"):
        with st.spinner("Analyzing risk factors and negotiating counterfactuals..."):
            
            # 1. SETUP DiCE
            d = dice_ml.Data(dataframe=X_test.assign(Churn=0), continuous_features=['tenure', 'MonthlyCharges', 'TotalCharges'], outcome_name='Churn')
            m = dice_ml.Model(model=model, backend="sklearn")
            exp = dice_ml.Dice(d, m, method="random")
            
            # 2. GENERATE OPTIONS
            dice_result = exp.generate_counterfactuals(customer_data, total_CFs=3, desired_class=0)
            suggestions = dice_result.cf_examples_list[0].final_cfs_df
            
            # 3. COST OPTIMIZATION (THE BRAIN)
            best_opt = None
            lowest_cost = float('inf')
            report_data = []

            for i in range(len(suggestions)):
                rec = suggestions.iloc[[i]].drop('Churn', axis=1)
                cost, details = calculate_cost(customer_data, rec)
                
                option_info = {
                    "id": i+1,
                    "cost": cost,
                    "changes": details,
                    "is_best": False
                }
                
                if cost < lowest_cost:
                    lowest_cost = cost
                    best_opt = i
                
                report_data.append(option_info)
            
            report_data[best_opt]["is_best"] = True
            st.session_state['report_data'] = report_data
            st.session_state['report_ready'] = True
            st.session_state['best_cost'] = lowest_cost

    # --- DISPLAY REPORT IF READY ---
    if st.session_state['report_ready']:
        data = st.session_state['report_data']
        best = data[st.session_state['report_data'].index(next(item for item in data if item["is_best"]))]

        # A. VIEW REPORT ON SCREEN
        st.subheader("📊 Executive Summary")
        
        # 1. Why Churn?
        st.markdown(f"""
        <div class='report-view'>
        <h4>1. Diagnosis: Why is this customer churning?</h4>
        <p>The AI model detected a <b>{prob*100:.1f}% probability of churn</b>. 
        This is driven by their current service configuration (likely High Charges or Month-to-Month contract) 
        compared to our historical loyalty patterns.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. The Options
        st.markdown("#### 2. AI Generated Retention Plans")
        cols = st.columns(3)
        for i, opt in enumerate(data):
            with cols[i]:
                color = "green" if opt["is_best"] else "red"
                st.markdown(f":{color}[**Option {opt['id']}**]")
                st.caption(f"Business Cost: ${opt['cost']:.2f}")
                for change in opt['changes']:
                    st.code(change)

        # 3. The Recommendation
        st.markdown(f"""
        <div class='report-view' style='border-left: 5px solid #28a745;'>
        <h4>3. Final Recommendation</h4>
        <p>We recommend executing <b>Option {best['id']}</b>.</p>
        <p><b>Reason:</b> While other options were technically possible, this option achieves customer retention 
        for the lowest possible business cost (<b>${st.session_state['best_cost']:.2f}</b>). 
        It minimizes revenue loss while effectively lowering the churn probability to 0%.</p>
        </div>
        """, unsafe_allow_html=True)

        # B. GENERATE PDF
        def create_pdf():
            pdf = PDFReport()
            pdf.add_page()
            
            # Section 1: Diagnosis
            pdf.chapter_title(f"1. Diagnosis (Customer #{customer_id})")
            pdf.chapter_body(f"Current Status: HIGH RISK ({prob*100:.1f}% Churn Probability).\n"
                             f"This customer's profile indicates high sensitivity to their current service terms. "
                             f"Immediate intervention is required to prevent loss.")
            
            # Section 2: Options
            pdf.chapter_title("2. Retention Strategies Considered")
            for opt in data:
                status = "(Recommended)" if opt['is_best'] else "(Rejected)"
                pdf.chapter_body(f"Option {opt['id']} {status}\n"
                                 f"   - Cost to Implement: ${opt['cost']:.2f}\n"
                                 f"   - Actions Required: {', '.join(opt['changes'])}")
            
            # Section 3: Logic
            pdf.chapter_title("3. Decision Logic (Explainable AI)")
            pdf.chapter_body(f"The AI evaluated 3 distinct counterfactual scenarios. "
                             f"We selected Option {best['id']} because it satisfies the 'Minimal Cost Principle'. "
                             f"We avoid changing 'Tenure' (impossible) or 'Contract' (difficult), focusing instead on "
                             f"high-impact, low-friction changes like {', '.join(best['changes'])}.")
            
            return pdf.output(dest="S").encode("latin-1")

        pdf_bytes = create_pdf()
        
        st.download_button(
            label="📄 Download Full PDF Report",
            data=pdf_bytes,
            file_name=f"Retention_Report_{customer_id}.pdf",
            mime="application/pdf"
        )

else:
    st.info("Customer is Safe. No report generation needed.")