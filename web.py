from flask import Flask, render_template_string, request
import json

app = Flask(__name__)

HTML = """
<!doctype html>
<html>
<head>
<title>PPP Monitor</title>
<script>
setInterval(() => location.reload(), 5000);
</script>
</head>
<body>
<h2>PPP Active Monitor</h2>

<form method="POST">
<textarea name="names" rows="10" cols="40" placeholder="Input PPP name"></textarea><br>
<button type="submit">Cek</button>
</form>

{% if results %}
<table border="1">
<tr><th>Name</th><th>IP</th><th>MAC</th><th>Uptime</th></tr>
{% for r in results %}
<tr>
<td>{{r.name}}</td>
<td>
{% if r.ip %}
<a href="http://{{r.ip}}" target="_blank">{{r.ip}}</a>
{% else %}
Not Connected
{% endif %}
</td>
<td>{{r.mac}}</td>
<td>{{r.uptime}}</td>
</tr>
{% endfor %}
</table>
{% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET","POST"])
def index():
    results = []

    if request.method == "POST":
        names = request.form.get("names","").splitlines()

        try:
            with open("ppp_active.json") as f:
                data = json.load(f)
        except:
            data = []

        for name in names:
            found = next((x for x in data if x["name"] == name.strip()), None)

            if found:
                results.append(found)
            else:
                results.append({
                    "name": name,
                    "ip": None,
                    "mac": "-",
                    "uptime": "-"
                })

    return render_template_string(HTML, results=results)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=1080)
