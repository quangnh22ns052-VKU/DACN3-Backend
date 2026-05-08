from core.detector import PhishDetector

detector = PhishDetector()

# Test the problematic URL
test_url = "https://gemini.google.com/app/44d36cb4ba265694"
result = detector.predict(test_url)

print(f"URL: {test_url}")
print(f"Prediction: {result['label']}")
print(f"Confidence: {result['probabilities']}")
print()

# Test other Google services
test_urls = [
    "https://gemini.google.com",
    "https://drive.google.com",
    "https://maps.google.com",
    "https://mail.google.com",
]

print("Testing Google services:")
for url in test_urls:
    result = detector.predict(url)
    print(f"  {url}: {result['label']}")
