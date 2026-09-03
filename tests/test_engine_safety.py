from pathlib import Path

ENGINE_DIR = Path("/home/kavin/.hermes/skills/productivity/job-application-autofill/scripts")


def test_engines_use_sandboxed_firefox_and_do_not_auto_click_apply():
    dump = (ENGINE_DIR / "jobform_dump.mjs").read_text()
    fill = (ENGINE_DIR / "jobform_fill.mjs").read_text()
    for source in (dump, fill):
        assert "firefox.launch" in source
        assert "chromium.launch" not in source
        assert "--no-sandbox" not in source
        assert "const openers =" not in source
    assert "execFileSync('python3', [queueCli, 'verify-authorization', auth, url]" in fill
    assert "resolved element is not an actual submit control" in fill
    assert "getByText(step.value" not in fill
    assert "await_security_code" not in fill
    assert "el.closest('label')?.click()" not in fill
