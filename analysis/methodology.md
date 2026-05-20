# Methodology

The workbench uses a transparent scoring model rather than an opaque machine-learning model. That choice matches a business analyst workflow where leaders need to understand the recommendation, challenge the assumptions, and assign owners quickly.

## Data Sources

- Public complaint themes come from a CFPB student-loan complaint download. The raw public file is used locally for issue taxonomy and is summarized into `data/public_complaint_themes.csv`.
- Borrower segments, daily metrics, intervention effects, and quality checks are synthetic. They are modeled on common lending operations structures: product type, channel, borrower count, average balance, delinquency, contact demand, application conversion, payment behavior, and servicing quality.

## Scoring Logic

The root-cause score combines delinquency rate, contact demand, income-pressure proxy, autopay gap, complaint theme concentration, metric confidence, approval rate, and volatility. Each cohort receives a primary root cause and a recommended intervention. Scenario value estimates the avoided loss risk from reducing delinquency, net of implementation effort.

## Why This Is Defensible

The artifact separates public external evidence from synthetic protected portfolio data. It does not claim to represent any lender's actual performance. It is designed to demonstrate how a borrower strategy analyst would structure ambiguity, check data quality, quantify tradeoffs, and recommend action.
