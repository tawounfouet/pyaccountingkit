"""L04-01: executable R&D invariants for an accounting-book *draft*.

No PostgreSQL, IAM, active book, journal, GL posting or IFRS compliance tests.
"""
from dataclasses import replace
from datetime import date

import pytest

from pyaccountingkit.company_configuration.domain.accounting_books import (
    AccountingBookConflict,
    AccountingBookDraft,
    BookCode,
    InvalidAccountingBook,
    require_unique_book_code,
)
from pyaccountingkit.company_configuration.domain.shared.accounting_scope import (
    ConfigurationScope,
)
from pyaccountingkit.company_configuration.domain.shared.effective_interval import (
    EffectiveInterval,
)
from pyaccountingkit.company_configuration.domain.shared.errors import VersionConflict
from pyaccountingkit.company_configuration.domain.shared.identifiers import (
    AccountingBookId,
    CompanyId,
    LegalEntityId,
)
from pyaccountingkit.company_configuration.domain.shared.references import (
    CurrencyCode,
    ReferenceFrameworkRef,
)


def draft(
    *,
    book_id: AccountingBookId | None = None,
    tenant: str = "tenant-a",
    company: CompanyId | None = None,
    entity: LegalEntityId | None = None,
    code: str = "MAIN",
    label: str = "General accounting",
    framework: str = "FR-PCG",
    version: str = "2026",
    start: date = date(2026, 1, 1),
    end: date | None = None,
    revision: int = 1,
) -> AccountingBookDraft:
    book_id = book_id or AccountingBookId.new()
    return AccountingBookDraft(
        id=book_id,
        scope=ConfigurationScope(
            tenant_id=tenant,
            company_id=company or CompanyId.new(),
            legal_entity_id=entity or LegalEntityId.new(),
            book_id=book_id,
        ),
        code=BookCode(code),
        label=label,
        currency=CurrencyCode("EUR"),
        framework=ReferenceFrameworkRef(framework, version),
        effective=EffectiveInterval(start, end),
        source_ref="business-request:l04-prototype",
        revision=revision,
    )


@pytest.mark.parametrize(
    ("framework", "version"),
    [
        ("FR-PCG", "2026"),
        ("IFRS", "2026"),
        ("OHADA-SYSCOHADA", "AUDCIF-2017"),
    ],
)
def test_versioned_framework_is_only_a_reference_not_a_compliance_assertion(
    framework, version
):
    book = draft(framework=framework, version=version)
    assert book.framework == ReferenceFrameworkRef(framework, version)
    assert book.scope.book_id == book.id
    assert book.revision == 1


@pytest.mark.parametrize(
    "code",
    ["", "lowercase", "BAD CODE", "_START", "A" * 33, " A", "ÉURO", "A/B"],
)
def test_book_code_is_conservative_canonical_rnd_value(code):
    with pytest.raises(InvalidAccountingBook):
        BookCode(code)


@pytest.mark.parametrize("code", ["A", "MAIN", "GAAP_2026", "A-B"])
def test_valid_book_codes_are_stable_value_objects(code):
    assert BookCode(code) == BookCode(code)


def test_company_entity_tenant_and_book_are_explicitly_scoped():
    book = draft()
    assert isinstance(book.id, AccountingBookId)
    assert book.scope.book_id == book.id
    assert book.scope.tenant_id == "tenant-a"


def test_wrong_book_id_in_scope_is_rejected():
    book = draft()
    wrong_scope = replace(book.scope, book_id=AccountingBookId.new())
    with pytest.raises(InvalidAccountingBook, match="matching book id"):
        replace(book, scope=wrong_scope)


def test_entity_level_scope_without_book_is_not_a_book_draft():
    book = draft()
    with pytest.raises(InvalidAccountingBook, match="matching book id"):
        replace(book, scope=replace(book.scope, book_id=None))


@pytest.mark.parametrize("label", ["", " ", " name ", "\n"])
def test_empty_or_untrimmed_label_is_rejected(label):
    with pytest.raises(InvalidAccountingBook, match="label"):
        replace(draft(), label=label)


@pytest.mark.parametrize("revision", [0, -1, True, 2.2, "2"])
def test_invalid_revision_is_rejected(revision):
    with pytest.raises(InvalidAccountingBook, match="revision"):
        replace(draft(), revision=revision)


@pytest.mark.parametrize("source", ["", " ", " stale "])
def test_source_provenance_cannot_be_blank_or_untrimmed(source):
    with pytest.raises(InvalidAccountingBook, match="source_ref"):
        replace(draft(), source_ref=source)


def test_must_use_typed_currency_and_versioned_framework():
    book = draft()
    with pytest.raises(InvalidAccountingBook, match="CurrencyCode"):
        replace(book, currency="EUR")
    with pytest.raises(InvalidAccountingBook, match="versioned framework"):
        replace(book, framework="IFRS")


def test_rename_produces_candidate_revision_without_changing_original():
    before = draft()
    after = before.rename("New label", expected_revision=1, reason="Review")

    assert before.label == "General accounting"
    assert before.revision == 1
    assert after.label == "New label"
    assert after.revision == 2
    assert before.id == after.id
    assert before.scope == after.scope


def test_rename_requires_expected_revision_and_nonblank_reason():
    book = draft()
    with pytest.raises(VersionConflict):
        book.rename("Updated", expected_revision=2, reason="Review")
    with pytest.raises(VersionConflict):
        book.rename("Updated", expected_revision=True, reason="Review")
    with pytest.raises(InvalidAccountingBook, match="reason"):
        book.rename("Updated", expected_revision=1, reason=" ")
    with pytest.raises(InvalidAccountingBook, match="change"):
        book.rename(book.label, expected_revision=1, reason="Valid")


def test_reframe_is_candidate_only_and_versioned():
    original = draft()
    replacement = ReferenceFrameworkRef("IFRS", "2026")
    after = original.reframe(replacement, expected_revision=1, reason="Proposal")
    assert after.framework == replacement
    assert original.framework.framework_code == "FR-PCG"
    assert after.revision == 2
    with pytest.raises(InvalidAccountingBook, match="change"):
        original.reframe(original.framework, expected_revision=1, reason="Proposal")


def test_entity_identity_ignores_label_revision_and_code_but_tenant_remains_key():
    book = draft()
    revision = book.rename("New", expected_revision=1, reason="Amendment")
    assert book == revision
    assert hash(book) == hash(revision)
    assert book != replace(book, scope=replace(book.scope, tenant_id="tenant-b"))
    assert book != draft()


def test_duplicate_code_overlapping_same_entity_is_rejected():
    company, entity = CompanyId.new(), LegalEntityId.new()
    first = draft(company=company, entity=entity, end=date(2027, 1, 1))
    second = draft(company=company, entity=entity, start=date(2026, 5, 1))
    with pytest.raises(AccountingBookConflict):
        require_unique_book_code(second, (first,))


def test_adjacent_periods_with_same_code_are_not_overlapping():
    company, entity = CompanyId.new(), LegalEntityId.new()
    previous = draft(company=company, entity=entity, end=date(2027, 1, 1))
    current = draft(company=company, entity=entity, start=date(2027, 1, 1))
    require_unique_book_code(current, (previous,))


def test_non_overlapping_periods_with_same_code_are_not_conflicts():
    company, entity = CompanyId.new(), LegalEntityId.new()
    prior = draft(company=company, entity=entity, end=date(2026, 7, 1))
    later = draft(company=company, entity=entity, start=date(2027, 1, 1))
    require_unique_book_code(later, (prior,))


def test_code_can_repeat_in_other_company_entity_or_tenant():
    company, entity = CompanyId.new(), LegalEntityId.new()
    primary = draft(company=company, entity=entity)
    alternatives = (
        draft(company=CompanyId.new(), entity=entity),
        draft(company=company, entity=LegalEntityId.new()),
        draft(tenant="tenant-b", company=company, entity=entity),
        draft(company=company, entity=entity, code="OTHER"),
    )
    for alternative in alternatives:
        require_unique_book_code(alternative, (primary,))


def test_a_new_revision_is_not_a_duplicate_of_its_own_book_id():
    book = draft()
    updated = book.rename("Revised", expected_revision=1, reason="Business request")
    require_unique_book_code(updated, (book,))


def test_existing_catalog_must_be_immutable_and_typed():
    book = draft()
    with pytest.raises(InvalidAccountingBook, match="immutable tuple"):
        require_unique_book_code(book, [book])
    with pytest.raises(InvalidAccountingBook, match="non-book"):
        require_unique_book_code(book, ("not-a-book",))
    with pytest.raises(InvalidAccountingBook, match="Expected"):
        require_unique_book_code("not-a-book", ())


def test_no_activation_posting_or_persistence_method_is_available():
    book = draft()
    assert not hasattr(book, "activate")
    assert not hasattr(book, "post")
    assert not hasattr(book, "save")
