def build_swift_command(
    binpath,
    server_address,
    bucket_id,
    client_hostname,
    client_name,
    exclude_title=False,
    exclude_titles=None,
    research_category_map=None,
):
    command = [binpath, server_address, bucket_id, client_hostname, client_name]
    if exclude_title:
        command.append("--exclude-title")
    for title in exclude_titles or []:
        command.extend(["--exclude-titles", title])
    if research_category_map is not None:
        command.append("--research")
        for pattern, category in research_category_map.items():
            command.extend(["--research-category", pattern, category])
    return command
