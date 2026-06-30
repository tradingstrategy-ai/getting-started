import copy

import nbformat

from getting_started.notebook_static_server import PROGRESS_OUTPUT_MESSAGE
from getting_started.notebook_static_server import add_table_of_contents
from getting_started.notebook_static_server import clean_progress_outputs
from getting_started.notebook_static_server import is_progress_stream_text


def test_add_table_of_contents_after_first_heading():
    body = """<!doctype html>
<html>
<head><title>Notebook</title></head>
<body>
<h1 id="Main-title">Main title<a class="anchor-link" href="#Main-title">&para;</a></h1>
<p>Intro</p>
<h2 id="Notebook-setup">Notebook setup<a class="anchor-link" href="#Notebook-setup">&para;</a></h2>
<h3 id="A,B(1)">A &amp; B &lt; C<a class="anchor-link" href="#A,B(1)">&para;</a></h3>
</body>
</html>
"""

    rendered = add_table_of_contents(body)

    assert rendered.index("</h1>") < rendered.index('<nav class="notebook-toc"')
    assert rendered.index('<nav class="notebook-toc"') < rendered.index("<p>Intro</p>")
    assert ".notebook-toc {" in rendered
    assert rendered.index(".notebook-toc {") < rendered.index("</head>")
    assert '<a href="#Notebook-setup">Notebook setup</a>' in rendered
    assert '<li class="notebook-toc-level-3"><a href="#A%2CB%281%29">A &amp; B &lt; C</a></li>' in rendered
    assert "&para;" not in rendered.split('<nav class="notebook-toc"', 1)[1].split("</nav>", 1)[0]
    assert "Table of contents" in rendered
    assert "href=\"#Table" not in rendered


def test_add_table_of_contents_returns_original_without_usable_headings():
    body = "<html><head></head><body><h1 id=\"Only\">Only</h1></body></html>"

    assert add_table_of_contents(body) == body


def test_is_progress_stream_text_requires_progress_markers():
    assert is_progress_stream_text("\rBacktesting strategy: 0%| | 0/10 [00:00<?, ?it/s]")
    assert is_progress_stream_text("\r  0%|          | 0/10 [00:00<?, ?it/s]")
    assert not is_progress_stream_text("12 it/s")
    assert not is_progress_stream_text("\r12 it/s")
    assert not is_progress_stream_text("\rnormal carriage return output")


def test_clean_progress_outputs_collapses_progress_and_preserves_outputs():
    nb = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell(
                outputs=[
                    nbformat.v4.new_output(
                        "stream",
                        name="stdout",
                        text="Using indicator cache /tmp/cache\n",
                    ),
                    nbformat.v4.new_output(
                        "stream",
                        name="stderr",
                        text="\rBacktesting strategy: 0%| | 0/10 [00:00<?, ?it/s]",
                    ),
                    nbformat.v4.new_output(
                        "stream",
                        name="stderr",
                        text="\rBacktesting strategy: 100%| | 10/10 [00:01<00:00, 10.00it/s]",
                    ),
                    nbformat.v4.new_output(
                        "display_data",
                        data={"text/plain": "result"},
                        metadata={},
                    ),
                ],
            )
        ],
    )
    original = copy.deepcopy(nb)

    cleaned = clean_progress_outputs(nb)

    assert nb == original
    outputs = cleaned.cells[0].outputs
    assert len(outputs) == 3
    assert outputs[0].text == "Using indicator cache /tmp/cache\n"
    assert outputs[1].output_type == "stream"
    assert outputs[1].name == "stderr"
    assert outputs[1].text == PROGRESS_OUTPUT_MESSAGE
    assert outputs[2].output_type == "display_data"


def test_clean_progress_outputs_preserves_mixed_stream_text():
    nb = nbformat.v4.new_notebook(
        cells=[
            nbformat.v4.new_code_cell(
                outputs=[
                    nbformat.v4.new_output(
                        "stream",
                        name="stderr",
                        text=(
                            "Using indicator cache /tmp/cache\n"
                            "\rBacktesting strategy: 0%| | 0/10 [00:00<?, ?it/s]\n"
                            "\rBacktesting strategy: 100%| | 10/10 [00:01<00:00, 10.00it/s]\n"
                            "Done\n"
                        ),
                    ),
                    nbformat.v4.new_output(
                        "stream",
                        name="stdout",
                        text="Throughput\r12 it/s\n",
                    ),
                ],
            )
        ],
    )

    cleaned = clean_progress_outputs(nb)
    outputs = cleaned.cells[0].outputs

    assert len(outputs) == 4
    assert outputs[0].text == "Using indicator cache /tmp/cache\n"
    assert outputs[1].text == PROGRESS_OUTPUT_MESSAGE
    assert outputs[2].text == "Done\n"
    assert outputs[3].text == "Throughput\r12 it/s\n"
