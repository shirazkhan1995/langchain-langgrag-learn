class Account:
    def __init__(self):
        self._balance = 100  # Single underscore: convention, discouraged but accessible
        self.__pin = 1234    # Double underscore: name mangling, harder to access

    def _get_balance(self):
        """Single underscore method - intended for internal use only"""
        return self._balance

    def __verify_pin(self, pin):
        """Double underscore method - name mangled to _Account__verify_pin"""
        return pin == self.__pin

    def withdraw(self, amount, pin):
        """Public method that uses private methods"""
        if self.__verify_pin(pin):
            if amount <= self._balance:
                self._balance -= amount
                return True
        return False


# Usage demonstration
account = Account()

# Single underscore - accessible but discouraged
print(account._balance)  # Output: 100

# Double underscore - name mangled
# account.__pin  # AttributeError: 'Account' object has no attribute '__pin'
print(account._Account__pin)  # Output: 1234 (name mangling)

######################################################
class WithdrawalError(Exception):
    """Domain-specific — catchable by type, reads better than a generic ValueError."""

try:
    result = account.withdraw(200, 1234)
    if not result:
        raise WithdrawalError("Insufficient funds or invalid PIN")
except ConnectionError as e:
    raise WithdrawalError("bank API unreachable") from e   # ← chaining
except WithdrawalError as e:
    print(f"handled: {e}")
else:
    print("Withdrawal successful!")     # only if no exception
finally:
    account.close()                     # always — cleanup

