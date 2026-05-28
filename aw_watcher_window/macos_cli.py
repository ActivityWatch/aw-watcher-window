def build_swift_command(
    binpath,
    server_address,
    bucket_id,
    client_hostname,
    client_name,
    exclude_title=False,
    exclude_titles=None,
):
    command = [binpath, server_address, bucket_id, client_hostname, client_name]
    if exclude_title:
        command.append("--exclude-title")
    for title in exclude_titles or []:
        command.extend(["--exclude-titles", title])
    return command
