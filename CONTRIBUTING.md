# Contributing

Thanks for helping improve the Instapaper API Python library. Bug reports, fixes, and documentation improvements are all welcome.

## Reporting issues

Open a [GitHub issue](https://github.com/Instapaper/instapaper-api-python/issues). Search existing issues first, and include:

- The library version (`instapaper.__version__`) and your Python version
- The method you called and the arguments you passed
- What you expected to happen and what happened instead, including the full traceback

Leave access tokens, client secrets, and Instaparser keys out of issues, logs, and code samples.

For questions about the API itself, such as endpoints, rate limits, or application approval, see the [developer documentation](https://www.instapaper.com/developers/overview/getting-started) or email support@instapaper.com.

### Security issues

Don't open a public issue for a security vulnerability. Email support@instapaper.com instead.

## Making changes

1. Fork the repository and create a branch from `main`.
2. Set up a development environment as described in [BUILD.md](BUILD.md).
3. Make your change, with tests.
4. Run the same checks CI runs:

   ```sh
   ruff check .
   ruff format --check .
   mypy instapaper tests examples
   pytest
   ```

5. Open a pull request that explains what changed and why.

### Guidelines

- **No runtime dependencies.** The library uses only the Python standard library. Development tools belong in the `dev` extra in `pyproject.toml`.
- **Python 3.10 and later.** CI runs on 3.10 through 3.13, so avoid features newer than 3.10.
- **Everything is typed.** mypy runs with `disallow_untyped_defs`, including on tests and examples.
- **Tests don't touch the network.** Use the `client` and `transport` fixtures from `tests/conftest.py`. `FakeTransport` records each request and returns responses you queue, so a test can assert on the method, URL, and body the client sent.
- **Match the API.** Parameter names, defaults, and validation should follow the [API reference](https://www.instapaper.com/developers/overview/getting-started). This library aims to behave the same as the official TypeScript SDK, so a change to shared behavior may need a matching change there.
- **Update the docs.** Add user-facing changes to the unreleased version at the top of [CHANGELOG.md](CHANGELOG.md), and update [README.md](README.md) when you add or change public API.

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
