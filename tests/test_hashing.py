"""
tests/test_hashing.py
=====================
Testes unitários para módulo de hashing.
"""

import pytest
import io
from core.models.pr_record import PRRecord
from utils.hashing import hash_content, hash_record,hash_file_stream


class TestHashContent:
    """Testes para hash_content()."""

    def test_hash_content_deterministic(self):
        """Mesmo conteúdo produz mesmo hash."""
        content = "exemplo de conteúdo para hash"
        hash1 = hash_content(content)
        hash2 = hash_content(content)
        assert hash1 == hash2

    def test_hash_content_different_input(self):
        """Conteúdos diferentes produzem hashes diferentes."""
        hash1 = hash_content("conteúdo 1")
        hash2 = hash_content("conteúdo 2")
        assert hash1 != hash2

    def test_hash_content_length(self):
        """Hash SHA-256 tem 64 caracteres (hex)."""
        hash_result = hash_content("teste")
        assert len(hash_result) == 64


class TestHashRecord:
    """Testes para hash_record()."""

    def test_hash_record_same_repo(self):
        """Dois PRs do mesmo repositório geram mesmo hash."""
        pr1 = PRRecord(
            id=1,
            html_url="https://github.com/repo/example/pull/10#comment-1",
            repo="repo/example",
            path="src/main.py",
            body="Descrição 1",
            diff_hunk="@@ -10,5 +10,5 @@",
            author="author1",
            author_association="CONTRIBUTOR",
            commit_id="abc123",
            line=10,
            language="Python",
            created_at="2024-01-01",
        )
        pr2 = PRRecord(
            id=2,
            html_url="https://github.com/repo/example/pull/11#comment-2",
            repo="repo/example",
            path="src/other.py",
            body="Descrição 2",
            diff_hunk="@@ -20,5 +20,5 @@",
            author="author2",
            author_association="MEMBER",
            commit_id="def456",
            line=20,
            language="Python",
            created_at="2024-01-02",
        )
        assert hash_record(pr1) == hash_record(pr2)

    def test_hash_record_different_repo(self):
        """PRs de repositórios diferentes geram hashes diferentes."""
        pr1 = PRRecord(
            id=1,
            html_url="https://github.com/repo/example1/pull/10#comment-1",
            repo="repo/example1",
            path="src/main.py",
            body="Descrição",
            diff_hunk="@@ -10,5 +10,5 @@",
            author="author",
            author_association="CONTRIBUTOR",
            commit_id="abc123",
            line=10,
            language="Python",
            created_at="2024-01-01",
        )
        pr2 = PRRecord(
            id=2,
            html_url="https://github.com/repo/example2/pull/10#comment-2",
            repo="repo/example2",
            path="src/main.py",
            body="Descrição",
            diff_hunk="@@ -10,5 +10,5 @@",
            author="author",
            author_association="CONTRIBUTOR",
            commit_id="abc123",
            line=10,
            language="Python",
            created_at="2024-01-01",
        )
        assert hash_record(pr1) != hash_record(pr2)

    def test_hash_record_length(self):
        """Hash do PR é SHA-256 válido (64 caracteres)."""
        pr = PRRecord(
            id=1,
            html_url="https://github.com/repo/test/pull/10#comment-1",
            repo="repo/test",
            path="src/main.py",
            body="Body",
            diff_hunk="@@ -10,5 +10,5 @@",
            author="author",
            author_association="CONTRIBUTOR",
            commit_id="abc123",
            line=10,
            language="Python",
            created_at="2024-01-01",
        )
        hash_result = hash_record(pr)
        assert len(hash_result) == 64

class TestHashFileStream:
    

    def test_hash_file_stream_correctness(self):
        """Calcula o hash corretamente em chunks e garante a reconstrução das linhas via generator."""
        conteudo_arquivo = "linha 1\nlinha 2\nlinha 3"
        stream_simulado = io.StringIO(conteudo_arquivo)

        digest, gerador_linhas = hash_file_stream(stream_simulado)

        # 1. Verifica se o gerador consome e retorna as linhas corretamente de forma preguiçosa
        linhas = list(gerador_linhas)
        assert linhas == ["linha 1\n", "linha 2\n", "linha 3"]

        # 2. Verifica se o hash calculado do stream é matematicamente idêntico ao do texto todo em memória
        hash_esperado = hash_content(conteudo_arquivo)
        assert digest == hash_esperado

    def test_hash_file_stream_empty(self):
        """Garante que um stream vazio gera o hash correto para string vazia e um gerador vazio."""
        stream_vazio = io.StringIO("")
        digest, gerador = hash_file_stream(stream_vazio)
        
        assert list(gerador) == []
        assert digest == hash_content("")
        
class TestHashingEncodingResilience:


    def test_hash_content_with_emojis_and_special_chars(self):
        """Garante que a codificação UTF-8 forçada suporta Emojis, Cyrillic e acentuação."""
        conteudo_complexo = "Bugfix no core 🐛. Alteração em repositório chinês (测试) e russo (тест)."
        
        try:
            hash_result = hash_content(conteudo_complexo)
        except UnicodeEncodeError:
            pytest.fail("hash_content falhou ao codificar caracteres especiais para UTF-8.")
            
        assert len(hash_result) == 64
        assert isinstance(hash_result, str)

    def test_hash_file_stream_ignores_multibyte_chunk_issues(self):
        """Valida se o cálculo do hash stream lida bem com strings multi-byte."""
        conteudo = "Primeira linha 🛠️\nSegunda linha: áéíóú\n"
        stream_simulado = io.StringIO(conteudo)

        digest, gerador = hash_file_stream(stream_simulado)
        
        # Verifica se o gerador não corrompeu os caracteres na hora de reconstruir a string
        linhas = list(gerador)
        assert linhas[0] == "Primeira linha 🛠️\n"
        assert linhas[1] == "Segunda linha: áéíóú\n"
        
        # O digest deve ser idêntico ao carregamento completo em memória
        assert digest == hash_content(conteudo)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
