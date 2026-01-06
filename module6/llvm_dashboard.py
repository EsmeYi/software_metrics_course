import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os

st.set_page_config(
    page_title="LLVM Measurement Program",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .metric-card {
        background-color: #262730;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #444;
        margin-bottom: 10px;
    }
    .metric-label {
        color: #aaaaaa;
        font-size: 14px;
    }
    .metric-value {
        color: #ffffff;
        font-size: 28px;
        font-weight: bold;
    }
    .metric-delta {
        font-size: 12px;
    }
    .metric-delta.positive { color: #00cc96; }
    .metric-delta.negative { color: #ef553b; }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def load_data():
    file_path = "daily_metrics.csv"
    if not os.path.exists(file_path):
        st.error(f"Data file '{file_path}' not found. Please run collection script first.")
        st.stop()
    
    df = pd.read_csv(file_path)
    df['date'] = pd.to_datetime(df['date'])
    return df.sort_values('date')

df = load_data()

st.sidebar.title("🛠️ Control Panel")
st.sidebar.markdown("---")

available_dates = df['date'].dt.date.unique()
selected_date = st.sidebar.selectbox(
    "📅 Select Snapshot Date",
    available_dates,
    index=len(available_dates)-1
)

current_data = df[df['date'].dt.date == selected_date].iloc[0]

prev_date_idx = df.index[df['date'].dt.date == selected_date][0] - 1
prev_data = df.iloc[prev_date_idx] if prev_date_idx >= 0 else None

history_df = df[df['date'].dt.date <= selected_date]

st.sidebar.markdown("---")
st.sidebar.info(f"Viewing data snapshot for: **{selected_date}**")
st.sidebar.markdown("Use this dropdown to generate daily screenshots for your report.")

def display_metric(label, value, prev_value, format_str="{}"):
    delta = 0
    delta_percent = 0
    color = "off"
    
    if prev_value is not None and prev_value != 0:
        delta = value - prev_value
        delta_percent = (delta / prev_value) * 100
        color = "normal"
        
    st.metric(
        label=label,
        value=format_str.format(value),
        delta=f"{delta_percent:.1f}%" if prev_value else None
    )

st.title(f"📊 LLVM Measurement Dashboard: {selected_date}")
st.markdown("Daily tracking of **11 Key Software Metrics**.")

st.header("1. Engineering Productivity & Flow")
c1, c2, c3, c4 = st.columns(4)

with c1:
    display_metric("Defect Inflow", current_data['inflow'], 
                   prev_data['inflow'] if prev_data is not None else None)
    st.caption("New issues created (Past 24h)")

with c2:
    display_metric("Defect Outflow", current_data['outflow'], 
                   prev_data['outflow'] if prev_data is not None else None)
    st.caption("Issues closed (Past 24h)")

with c3:
    display_metric("Code Churn", current_data['churn'], 
                   prev_data['churn'] if prev_data is not None else None)
    st.caption("Lines added + deleted")

with c4:
    display_metric("Active Authors", current_data['active_authors'], 
                   prev_data['active_authors'] if prev_data is not None else None)
    st.caption("Unique contributors (Past 24h)")

=st.subheader("📉 Trend: Inflow vs. Outflow")
fig_io = go.Figure()
fig_io.add_trace(go.Scatter(x=history_df['date'], y=history_df['inflow'], name='Inflow', line=dict(color='#ef553b')))
fig_io.add_trace(go.Scatter(x=history_df['date'], y=history_df['outflow'], name='Outflow', line=dict(color='#00cc96')))
fig_io.update_layout(height=300, margin=dict(l=20, r=20, t=30, b=20))
st.plotly_chart(fig_io, use_container_width=True)


st.markdown("---")
st.header("2. Code Health & Maintainability")
col_h1, col_h2, col_h3 = st.columns(3)

with col_h1:
    mi_val = current_data['mi']
    fig_mi = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = mi_val,
        title = {'text': "Maintainability Index (MI)"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "lightgray"},
            'steps': [
                {'range': [0, 65], 'color': "#ef553b"},   # Red: Hard to maintain
                {'range': [65, 85], 'color': "#f1c40f"},  # Yellow: Moderate
                {'range': [85, 100], 'color': "#00cc96"}  # Green: Good
            ],
            'threshold': {'line': {'color': "black", 'width': 4}, 'thickness': 0.75, 'value': mi_val}
        }
    ))
    fig_mi.update_layout(height=250, margin=dict(l=30, r=30, t=50, b=30))
    st.plotly_chart(fig_mi, use_container_width=True)

with col_h2:
    st.markdown("##### Technical Debt (SATD)")
    display_metric("SATD Count", current_data['satd'], 
                   prev_data['satd'] if prev_data is not None else None)
    st.markdown("##### Complexity Risk")
    display_metric("Avg Cyclomatic Complexity", current_data['avg_complexity'], 
                   prev_data['avg_complexity'] if prev_data is not None else None, "{:.2f}")

with col_h3:
    st.markdown("##### Documentation")
    dens = current_data['comment_density']
    st.metric("Comment Density", f"{dens:.1%}")
    st.progress(min(dens, 1.0))
    st.caption("Target: > 10%")
    
    st.markdown("##### Project Scale")
    st.metric("Total NLOC", f"{int(current_data['nloc']):,}")


st.markdown("---")
st.header("3. Process Efficiency & Stability Risk")

r1, r2, r3 = st.columns(3)

with r1:
    st.metric("Review Window", f"{current_data['review_window']:.1f} hrs", help="Avg time to close PRs")
    st.area_chart(history_df.set_index('date')['review_window'], height=150)

with r2:
    st.metric("Patch Rejection Rate", f"{current_data['rejection_rate']:.1%}", help="% of PRs closed without merge")
    st.line_chart(history_df.set_index('date')['rejection_rate'], height=150)

with r3:
    st.metric("Change Entropy", f"{current_data['change_entropy']:.4f}", help="Hassan (2009): Complexity of changes")
    fig_ent = px.bar(history_df, x='date', y='change_entropy')
    fig_ent.update_traces(marker_color='#FF4B4B')
    fig_ent.update_layout(
        height=150, 
        margin=dict(l=0, r=0, t=0, b=0),
        xaxis_title=None,
        yaxis_title=None,
        showlegend=False
    )
    st.plotly_chart(fig_ent, use_container_width=True, config={'displayModeBar': False})

st.markdown("---")
st.caption("Data Source: LLVM-Project Repository & GitHub API")