from pylsl import StreamInlet, resolve_streams
import time

def main():
    print("Looking for Muse EEG stream over LSL...")

    # Get all streams seen in the next 5 seconds
    all_streams = resolve_streams(wait_time=5)

    if not all_streams:
        print("No LSL streams found at all. Is BlueMuse streaming?")
        return

    print("Discovered streams:")
    for info in all_streams:
        print(f"  - name={info.name()} | type={info.type()} | "
              f"ch={info.channel_count()} | rate={info.nominal_srate()}")

    # Filter for EEG type
    eeg_streams = [s for s in all_streams if s.type() == 'EEG']

    if not eeg_streams:
        print("\nNo streams with type='EEG' found. "
              "Check BlueMuse LSL Bridge and try again.")
        return

    info = eeg_streams[0]
    print("\nUsing EEG stream:")
    print("  Name:", info.name())
    print("  Type:", info.type())
    print("  Channel count:", info.channel_count())
    print("  Nominal rate:", info.nominal_srate())

    inlet = StreamInlet(info, max_buflen=60)  # 60s buffer

    print("\nStarting to read samples for ~10 seconds...\n")
    start_time = time.time()
    sample_count = 0

    while time.time() - start_time < 10:
        sample, timestamp = inlet.pull_sample(timeout=1.0)
        if sample is not None:
            sample_count += 1
            if sample_count % 50 == 0:
                print(f"t={timestamp:.3f}, sample[0..3]={sample[:4]}")

    elapsed = time.time() - start_time
    if elapsed > 0:
        print(f"\nReceived {sample_count} samples in {elapsed:.2f} seconds "
              f"(~{sample_count/elapsed:.1f} Hz)")
    else:
        print("\nFinished, but elapsed time was ~0s?")

if __name__ == "__main__":
    main()
