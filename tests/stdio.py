"""External JSONL worker fixture; never included in student distributions."""

from pathlab.worker import serve_plugin

if __name__ == "__main__":
    serve_plugin("student_template.algorithm:StudentAlgorithm")
