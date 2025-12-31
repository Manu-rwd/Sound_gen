"""Analyze ECG session data."""
import json
from pathlib import Path

# Read the session file
session_file = Path("sessions/ecg_test_10s.jsonl")
chunks = []

with open(session_file) as f:
    for line in f:
        chunks.append(json.loads(line))

print(f"📊 ECG Session Analysis: {session_file.name}")
print("=" * 60)
print(f"Total chunks: {len(chunks)}")
print(f"Total samples: {sum(c['sample_count'] for c in chunks)}")
print(f"Duration: {chunks[-1]['timestamp_end']:.2f}s")
print()

# Feature statistics across all chunks
all_means = [c['features']['mean'] for c in chunks]
all_stds = [c['features']['std'] for c in chunks]
all_mins = [c['features']['min'] for c in chunks]
all_maxs = [c['features']['max'] for c in chunks]

print("📈 Feature Statistics Across All Chunks:")
print("-" * 60)
print(f"Mean ECG value: {sum(all_means)/len(all_means):.2f}")
print(f"  Range: {min(all_means):.2f} - {max(all_means):.2f}")
print()
print(f"Average std dev: {sum(all_stds)/len(all_stds):.2f}")
print(f"  Range: {min(all_stds):.2f} - {max(all_stds):.2f}")
print()
print(f"Global min value: {min(all_mins):.0f}")
print(f"Global max value: {max(all_maxs):.0f}")
print()

# Show first and last chunk
print("📝 First Chunk:")
print(json.dumps(chunks[0], indent=2))
print()
print("📝 Last Chunk:")
print(json.dumps(chunks[-1], indent=2))
