# gh-name-check

username checker & generator that hits github's signup endpoint.

## how it works
- `generator.py` generates random usernames and checks availability
- `checker.py` batch-checks usernames from text files
- both hit `/signup_check_new/username` — no api token needed

## usage
1. put usernames in `lists/`
2. run `python src/checker.py`
3. available ones land in `confirmed/`

## false positives / negatives
the endpoint lies sometimes. dont trust it blindly.
