import platform


full_path = ""
if platform.system() != "Darwin":
    full_path = "/home/ubuntu/email-article/"

filename = "{}migrations/env.py".format(full_path)

with open(filename, "r") as f:
    py_script = f.read()

string = "context.configure(connection=connection,"
insert_at_index = py_script.find(string) + len(string)
modified_py_script = (
    py_script[:insert_at_index] +
    " render_as_batch=True," +
    py_script[insert_at_index:]
)
with open(filename, "w") as f:
    f.write(modified_py_script)
