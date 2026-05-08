import pandas as pd

# Read current dataset
df = pd.read_csv('data/dataset.csv')

# Add more legitimate URLs with various patterns
additional_urls = [
    # Google Drive variations
    'https://drive.google.com/drive/my-drive',
    'https://drive.google.com/file/d/123456',
    'https://drive.google.com/open?id=123456',
    # More Google services
    'https://calendar.google.com',
    'https://contacts.google.com',
    'https://keep.google.com',
    'https://tasks.google.com',
    'https://news.google.com',
    # More subdomains
    'https://accounts.google.com',
    'https://support.google.com',
    'https://developers.google.com',
    # More app variations
    'https://app.github.com',
    'https://app.gitlab.com',
    'https://app.figma.com',
    'https://app.jira.cloud.com',
    'https://app.monkeytype.com',
    # More AWS variations
    'https://ec2.amazonaws.com',
    'https://s3.amazonaws.com',
    'https://lambda.amazonaws.com',
    # API endpoints
    'https://api.github.com/user',
    'https://api.stripe.com',
    'https://api.anthropic.com',
    'https://api.cohere.com',
]

# Create new rows
new_rows = pd.DataFrame({
    'url': additional_urls,
    'label': ['safe'] * len(additional_urls)
})

# Combine
df_combined = pd.concat([df, new_rows], ignore_index=True)
# Remove duplicates (keep first occurrence)
df_combined = df_combined.drop_duplicates(subset=['url'], keep='first')

df_combined.to_csv('data/dataset.csv', index=False)

# Show stats
print("✅ Dataset expanded!")
print(f"Total URLs: {len(df_combined)}")
print(f"Phishing: {(df_combined['label'] == 'phishing').sum()}")
print(f"Safe: {(df_combined['label'] == 'safe').sum()}")
