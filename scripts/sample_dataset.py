import pandas as pd
import sys

ratings_in = sys.argv[1]
ratings_out = sys.argv[2]
n = int(sys.argv[3])

df = pd.read_csv(ratings_in).sample(n)
df.to_csv(ratings_out, index=False)

print("Sample saved:", ratings_out)
