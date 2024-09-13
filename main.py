import re

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# Read the data
with open('data.txt', 'r') as file:
    lines = file.readlines()

# Extract relevant information
data = []
for line in lines:
    match = re.search(r'\[(\d+\.\d+)\] .* icmp_seq=(\d+) .* time=(\d+) ms', line)
    if match:
        timestamp = float(match.group(1))
        seq = int(match.group(2))
        rtt = int(match.group(3))
        data.append((timestamp, seq, rtt))

df = pd.DataFrame(data, columns=['timestamp', 'seq', 'rtt'])
df['datetime'] = pd.to_datetime(df['timestamp'], unit='s')

# Calculate statistics
total_requests = df['seq'].max() + 1  # +1 because seq starts at 0
total_replies = len(df)
delivery_rate = total_replies / total_requests

# Find longest consecutive successful pings
df['diff'] = df['seq'].diff()
df['success_group'] = (df['diff'] != 1).cumsum()
success_groups = df.groupby('success_group')
consecutive_success = success_groups.size().max()
longest_success_group = success_groups.size().idxmax()
longest_success_range = df[df['success_group'] == longest_success_group]['seq'].agg(['min', 'max'])

# Find longest burst of losses
df['loss_group'] = (df['diff'] == 1).cumsum()
loss_groups = df.groupby('loss_group')
longest_burst_losses = loss_groups.size().max()
longest_loss_group = loss_groups.size().idxmax()
longest_loss_range = df[df['loss_group'] == longest_loss_group]['seq'].agg(['min', 'max'])

# Calculate conditional probabilities
df_full = pd.DataFrame({'seq': range(total_requests)})
df_full = df_full.merge(df[['seq']], how='left', on='seq', indicator=True)
df_full['received'] = df_full['_merge'] == 'both'
df_full['prev_received'] = df_full['received'].shift(1)
prob_success_given_success = df_full[(df_full['received'] == True) & (df_full['prev_received'] == True)].shape[0] / \
                             df_full[df_full['prev_received'] == True].shape[0]
prob_success_given_failure = df_full[(df_full['received'] == True) & (df_full['prev_received'] == False)].shape[0] / \
                             df_full[df_full['prev_received'] == False].shape[0]

# RTT statistics
min_rtt = df['rtt'].min()
max_rtt = df['rtt'].max()

# Prepare report
report = f"""
1. Overall delivery rate: {delivery_rate:.2%}

2. Longest consecutive string of successful pings: {consecutive_success}
   Range: {longest_success_range['min']} to {longest_success_range['max']}

3. Longest burst of losses: {longest_burst_losses}
   Range: {longest_loss_range['min']} to {longest_loss_range['max']}

4. Correlation of packet loss:
   - P(success | previous success) = {prob_success_given_success:.2%}
   - P(success | previous failure) = {prob_success_given_failure:.2%}
   - Unconditional delivery rate: {delivery_rate:.2%}

5. Minimum RTT: {min_rtt} ms

6. Maximum RTT: {max_rtt} ms
"""

print(report)

# Create graphs
plt.figure(figsize=(12, 6))
plt.plot(df['datetime'], df['rtt'])
plt.xlabel('Time')
plt.ylabel('RTT (ms)')
plt.title('RTT over Time')
plt.savefig('rtt_over_time.png', dpi=300)
plt.close()

plt.figure(figsize=(10, 6))
sns.histplot(df['rtt'], kde=True)
plt.xlabel('RTT (ms)')
plt.ylabel('Frequency')
plt.title('Distribution of RTTs')
plt.savefig('rtt_histogram.png', dpi=300)
plt.close()

plt.figure(figsize=(10, 6))
plt.scatter(df['rtt'][:-1], df['rtt'][1:], alpha=0.2)
plt.xlabel('RTT of ping #N (ms)')
plt.ylabel('RTT of ping #N+1 (ms)')
plt.title('Correlation between consecutive RTTs')
plt.savefig('rtt_correlation.png', dpi=300)
plt.close()
