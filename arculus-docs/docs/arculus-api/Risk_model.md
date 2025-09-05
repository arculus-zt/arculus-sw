# Drone Telemetry Risk Model
 
This document describes the **Bayesian Risk Model** and the **Zero-Trust (ZT) Grading System** implemented for evaluating the security posture of drones in missions such as **surveillance** and **monitoring**.
 
---
 
## 1. Overview
 
Drones engaged in critical missions generate telemetry data that can be analyzed to estimate the likelihood of compromise.  
The **Bayesian Risk Model** uses four telemetry features to compute a **risk score**:
 
- **Transmission Rate**
- **Energy Consumption**
- **Unauthorized Access Attempts**
- **Signal Strength**
 
This risk score provides a probabilistic measure of drone trustworthiness.  
A higher score indicates **higher risk** (i.e., lower trust in the drone’s security state).
 
---
 
## 2. Bayesian Risk Score
 
The Bayesian risk score is calculated from telemetry data and mapped onto a **0–100 scale** using function computeBayesianRisk.
 
### Implementation Details
 
1. **Discretization of Telemetry Data**  
   - Continuous telemetry values are converted into binary indicators (normal vs. abnormal).  
   - Example: if the transmission rate exceeds a threshold, it is marked as abnormal (1), otherwise normal (0).  
   - Different thresholds are applied to each feature to reflect expected operating conditions.
 
2. **Attack Likelihood Estimation**  
   - Three potential attack types are modeled: **Flooder**, **Faker**, and **Physical Capture**.  
   - Each attack type is influenced by the four telemetry features with different weights.  
     - *Flooder* is primarily influenced by abnormal transmission rates.  
     - *Faker* is mostly influenced by unusual energy consumption.  
     - *Physical Capture* is strongly linked to signal strength anomalies.  
   - For each attack type, a weighted probability is computed to represent its likelihood.
 
3. **Trust Calculation**  
   - The attack probabilities are combined using a conditional probability distribution (CPD).  
   - The CPD maps all possible combinations of attacks to a final **Trust score** (probability that the drone is behaving correctly).  
   - The Bayesian network ensures that dependencies between multiple anomalies are accounted for, rather than treating them independently.
 
4. **Risk Conversion**  
   - The trust score is inverted into a risk score:  
     \[
     \text{Risk} = (1 - \text{Trust}) \times 100
     \]  
   - This ensures that a lower trust value translates to a higher risk score.
 
**Interpretation of the Risk Score**:
- **0** → Minimal risk (drone highly trusted)  
- **100** → Maximum risk (drone highly compromised)  
 
---
 
## 3. Zero-Trust Grade
 
Once the Bayesian risk score is obtained, it is converted into a **Zero-Trust grade** using function computeZTGrade.  
This grade provides a categorical assessment for operational decision-making:
 
- **A** → Very High Risk (critical concern)  
- **B** → High Risk  
- **C** → Moderate Risk  
- **D** → Low Risk  
- **E** → Minimal Risk  
 
The grade helps operators quickly interpret telemetry-driven risk levels without analyzing raw metrics.
 
---
 
## 4. Workflow Summary
 
1. **Collect telemetry** from drones in real missions.  
2. **Compute Bayesian Risk Score** to quantify the level of trust or compromise.  
3. **Assign a Zero-Trust Grade** for easy operational decision-making.  
 
This workflow transforms raw telemetry into **actionable intelligence**, enabling secure, trust-aware deployment of drones in sensitive environments.
 
---
 
## 5. Contribution
 
This model integrates **Bayesian reasoning** and **Zero-Trust principles** to provide both **quantitative** (risk score) and **qualitative** (ZT grade) measures of drone trustworthiness.  
It enables **mission-critical decision-making** by providing real-time security insights from telemetry data, supporting safer operations in surveillance, monitoring, and other sensitive applications.