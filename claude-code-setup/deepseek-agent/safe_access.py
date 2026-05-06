"""Safe access stubs."""
def is_allowed(*a, **kw): return True
def safe_join(*a, **kw): return "/"
def check_dangerous_cmd(*a, **kw): return False
def check_dangerous_write(*a, **kw): return False
def check_hostile(*a, **kw): return False
def check_file_size(*a, **kw): return True
def check_write_size(*a, **kw): return True
def check_network_access(*a, **kw): return True
def check_web_rate_limit(*a, **kw): return True
def check_web_url(*a, **kw): return True
