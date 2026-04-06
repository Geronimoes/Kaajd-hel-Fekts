import re

with open("app/routes.py", "r") as f:
    content = f.read()

# Add the delete route
delete_route = """
@main_bp.route("/api/chat/<int:chat_id>/delete", methods=["POST"])
@auth.login_required
def delete_chat_route(chat_id: int):
    context = get_chat_context(chat_id, db_path=current_app.config.get("DATABASE_PATH"))
    if not context:
        return jsonify({"error": "chat_not_found"}), 404

    # delete from DB
    deleted = delete_chat(chat_id, db_path=current_app.config.get("DATABASE_PATH"))
    
    # optionally delete the output dir as well
    output_dir = context.get("chat", {}).get("output_dir")
    if output_dir:
        out_path = Path(output_dir)
        if out_path.exists() and out_path.is_dir():
            shutil.rmtree(out_path, ignore_errors=True)

    return jsonify({"success": True, "deleted": deleted})
"""

content += delete_route
with open("app/routes.py", "w") as f:
    f.write(content)
