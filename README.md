# Butterfly Engine

> "One small decision, thousands of possible futures."

### What is Butterfly Engine?
Traditional financial models are rigid—they give you a single straight-line forecast. But the real business world is chaotic and uncertain. 

Butterfly Engine is a Monte Carlo Business Simulation & Decision-Support tool built with Python and Streamlit. Instead of predicting just one future, it simulates thousands of possible futures simultaneously. It helps founders, financial planners, and operators stress-test their strategies against market volatility before risking real capital.

### How Does It Work Under the Hood?

The engine operates on a probabilistic simulation loop rather than fixed arithmetic:

1. Baseline Assumptions (Sidebar Config): You feed your core financial inputs—starting cash, monthly revenue, fixed costs, gross margins, and growth uncertainty.
2. Strategy Design: You configure different operational strategies (e.g., Conservative, Growth, Balanced) by adjusting parameters like marketing budget percentage, number of new hires, and protected cash reserves.
3. The Simulation Loop (Monte Carlo Core): 
   * For every strategy, the engine runs thousands of simulated monthly cycles.
   * At each month, it introduces random market shocks using a normal distribution scaled by your volatility settings.
   * It applies real-world business dynamics, such as diminishing returns on marketing spend and incremental growth boosts from new hires.
4. Risk & Survival Tracking: It monitors whether total cash falls below zero or if operating cash runs out forcing the business to dip into reserves.
5. Database Persistence: You can save your experiment parameters, strategies, and summary results securely into a MySQL database for future audits and comparison.

### Key Features

* Monte Carlo Probabilistic Forecasting: Captures market risk by running thousands of parallel trajectories instead of flat numbers.
* Interactive Fan Charts (Plotly): Visualizes the median cash trajectory alongside 5th–95th percentile confidence bands to show best-case and worst-case bounds.
* Side-by-Side Strategy Comparison: Instantly evaluates survival probability, cash shortfall risks, and median ending cash across multiple strategies.
* Growth Sensitivity Analysis: Tests how sensitive your business survival is to shifts in baseline monthly growth rates.
* MySQL Experiment History: Save and load past simulation runs to track how strategy decisions evolve over time.

### Tech Stack

* Frontend / Dashboard: Streamlit
* Simulation Core: Python, NumPy, Pandas
* Visualizations: Plotly (Express & Graph Objects)
* Database & Persistence: MySQL (mysql-connector-python)

### Quick Start

1. Clone the repository:
   git clone https://github.com/your-username/butterfly-engine.git
   cd butterfly-engine

2. Install dependencies:
   pip install -r requirements.txt

3. Configure Environment Variables (.env):
   Set up your local MySQL credentials:
   MYSQL_HOST=localhost
   MYSQL_PORT=3306
   MYSQL_USER=root
   MYSQL_PASSWORD=your_password
   MYSQL_DATABASE=butterfly_engine

4. Run the Dashboard:
   streamlit run app.py
