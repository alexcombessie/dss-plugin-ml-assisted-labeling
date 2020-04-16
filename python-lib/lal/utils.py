import dataiku


def increment_queries_session(queries_ds_name):
    session_var_name = f'ML-ASSISTED-LABELING__{queries_ds_name}__session'
    variables = dataiku.Project().get_variables()
    session_id = variables['standard'].get(session_var_name, 0) + 1
    variables['standard'][session_var_name] = session_id
    dataiku.Project().set_variables(variables)
    return session_id


def get_current_session_id(queries_ds_name=None):
    if queries_ds_name is None:
        return 0
    return dataiku.Project().get_variables()['standard'].get(f'ML-ASSISTED-LABELING__{queries_ds_name}__session')