import argparse
import sys
import os

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.app.pipeline import Pipeline

def main():
    parser = argparse.ArgumentParser(description="SIH26146 - Backend MVP Pipeline")
    parser.add_argument("--input", type=str, required=True, help="Path to input dataset (CSV/JSON/XML)")
    parser.add_argument("--output_dir", type=str, default="backend/outputs", help="Directory to save output files")
    parser.add_argument("--contamination", type=float, default=0.26, help="Isolation Forest contamination parameter. Default 0.26 for controlled validation.")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.input):
        print(f"Error: Input file {args.input} does not exist.")
        sys.exit(1)
        
    pipeline = Pipeline(input_path=args.input, output_dir=args.output_dir, contamination=args.contamination)
    pipeline.run()

if __name__ == "__main__":
    main()
