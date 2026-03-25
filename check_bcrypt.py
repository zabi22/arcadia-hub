try:
    import bcrypt
    print("bcrypt available")
except ImportError:
    print("bcrypt not available")
