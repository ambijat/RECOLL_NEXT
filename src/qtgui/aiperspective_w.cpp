/* Copyright (C) 2026 Recoll Next contributors
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */
#include "aiperspective_w.h"

#include <QComboBox>
#include <QCoreApplication>
#include <QDir>
#include <QFileDialog>
#include <QFileInfo>
#include <QFormLayout>
#include <QHBoxLayout>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <QLabel>
#include <QLineEdit>
#include <QListWidget>
#include <QProgressBar>
#include <QPushButton>
#include <QSettings>
#include <QTextBrowser>
#include <QTimer>
#include <QVBoxLayout>
#include <QWidget>

namespace {

const char *settingsKeyStore = "/RecollNext/ai/store";

QString envValue(const char *name)
{
    return QString::fromLocal8Bit(qgetenv(name)).trimmed();
}

QString evidenceLabel(const QJsonObject& evidence, int position)
{
    QString label = evidence.value("title").toString().trimmed();
    if (label.isEmpty())
        label = evidence.value("path").toString().trimmed();
    if (label.isEmpty())
        label = evidence.value("document_id").toString().trimmed();
    if (label.isEmpty())
        label = QObject::tr("Untitled evidence");

    const double similarity = evidence.value("similarity").toDouble(-1.0);
    if (similarity >= 0.0) {
        return QString("[%1] %2  ·  %3")
            .arg(position)
            .arg(label)
            .arg(similarity, 0, 'f', 3);
    }
    return QString("[%1] %2").arg(position).arg(label);
}

} // namespace

AIPerspectiveDock::AIPerspectiveDock(QWidget *parent)
    : QDockWidget(tr("AI Perspective"), parent), m_process(new QProcess(this))
{
    setObjectName("recollNextAIPerspectiveDock");
    setAllowedAreas(Qt::LeftDockWidgetArea | Qt::RightDockWidgetArea);
    setMinimumWidth(360);

    auto *body = new QWidget(this);
    auto *layout = new QVBoxLayout(body);

    auto *promise = new QLabel(
        tr("Local Ollama perspectives over traceable Recoll evidence."), body);
    promise->setWordWrap(true);
    layout->addWidget(promise);

    auto *form = new QFormLayout();
    m_queryEdit = new QLineEdit(body);
    m_queryEdit->setPlaceholderText(tr("Run a Recoll search or enter a question"));
    form->addRow(tr("Query"), m_queryEdit);

    auto *storeRow = new QWidget(body);
    auto *storeLayout = new QHBoxLayout(storeRow);
    storeLayout->setContentsMargins(0, 0, 0, 0);
    m_storeEdit = new QLineEdit(storeRow);
    m_storeEdit->setPlaceholderText(tr("Semantic SQLite store"));
    auto *browseButton = new QPushButton(tr("Browse…"), storeRow);
    storeLayout->addWidget(m_storeEdit, 1);
    storeLayout->addWidget(browseButton);
    form->addRow(tr("Knowledge scope"), storeRow);

    m_viewCombo = new QComboBox(body);
    m_viewCombo->addItem(tr("Answer"), "answer");
    m_viewCombo->addItem(tr("Summary"), "summary");
    m_viewCombo->addItem(tr("Timeline"), "timeline");
    m_viewCombo->addItem(tr("Contradictions"), "contradictions");
    m_viewCombo->addItem(tr("Decisions"), "decisions");
    m_viewCombo->addItem(tr("Actions"), "actions");
    form->addRow(tr("Perspective"), m_viewCombo);
    layout->addLayout(form);

    auto *buttons = new QHBoxLayout();
    m_searchButton = new QPushButton(tr("Concept Search"), body);
    m_askButton = new QPushButton(tr("Ask AI"), body);
    m_cancelButton = new QPushButton(tr("Cancel"), body);
    m_cancelButton->setEnabled(false);
    buttons->addWidget(m_searchButton);
    buttons->addWidget(m_askButton);
    buttons->addStretch(1);
    buttons->addWidget(m_cancelButton);
    layout->addLayout(buttons);

    m_progress = new QProgressBar(body);
    m_progress->setRange(0, 1);
    m_progress->setValue(0);
    m_progress->setFormat(tr("Ready"));
    layout->addWidget(m_progress);

    layout->addWidget(new QLabel(tr("Perspective"), body));
    m_answerView = new QTextBrowser(body);
    m_answerView->setOpenExternalLinks(false);
    m_answerView->setPlaceholderText(
        tr("Choose a knowledge scope, then search or ask for a local perspective."));
    layout->addWidget(m_answerView, 2);

    layout->addWidget(new QLabel(tr("Evidence — double-click to open"), body));
    m_evidenceList = new QListWidget(body);
    m_evidenceList->setWordWrap(true);
    layout->addWidget(m_evidenceList, 1);

    setWidget(body);

    QSettings settings;
    QString store = envValue("RECOLL_AI_STORE");
    if (store.isEmpty())
        store = settings.value(settingsKeyStore).toString();
    if (store.isEmpty()) {
        const QString academic = QDir::current().filePath(
            ".local/booklibrandom-pdfs.sqlite3");
        const QString general = QDir::current().filePath(".local/semantic.sqlite3");
        store = QFileInfo::exists(academic) ? academic : general;
    }
    m_storeEdit->setText(QDir::toNativeSeparators(store));

    connect(browseButton, &QPushButton::clicked,
            this, &AIPerspectiveDock::browseStore);
    connect(m_searchButton, &QPushButton::clicked,
            this, &AIPerspectiveDock::startSearch);
    connect(m_askButton, &QPushButton::clicked,
            this, &AIPerspectiveDock::startAsk);
    connect(m_cancelButton, &QPushButton::clicked,
            this, &AIPerspectiveDock::cancelOperation);
    connect(m_process, &QProcess::readyReadStandardOutput,
            this, &AIPerspectiveDock::collectStandardOutput);
    connect(m_process, &QProcess::readyReadStandardError,
            this, &AIPerspectiveDock::collectStandardError);
    connect(m_process,
            QOverload<int, QProcess::ExitStatus>::of(&QProcess::finished),
            this, &AIPerspectiveDock::processFinished);
    connect(m_process, &QProcess::errorOccurred,
            this, &AIPerspectiveDock::processError);
    connect(m_evidenceList, &QListWidget::itemDoubleClicked,
            this, &AIPerspectiveDock::openEvidence);
}

void AIPerspectiveDock::setQuery(const QString& query)
{
    if (!query.trimmed().isEmpty())
        m_queryEdit->setText(query.trimmed());
}

void AIPerspectiveDock::browseStore()
{
    const QString selected = QFileDialog::getOpenFileName(
        this, tr("Choose semantic knowledge store"), m_storeEdit->text(),
        tr("SQLite stores (*.sqlite3 *.sqlite *.db);;All files (*)"));
    if (selected.isEmpty())
        return;
    m_storeEdit->setText(QDir::toNativeSeparators(selected));
    QSettings().setValue(settingsKeyStore, selected);
}

void AIPerspectiveDock::startSearch()
{
    startOperation(Operation::Search);
}

void AIPerspectiveDock::startAsk()
{
    startOperation(Operation::Ask);
}

void AIPerspectiveDock::startOperation(Operation operation)
{
    if (m_process->state() != QProcess::NotRunning)
        return;
    const QString query = m_queryEdit->text().trimmed();
    const QString store = QDir::fromNativeSeparators(m_storeEdit->text().trimmed());
    if (query.isEmpty()) {
        showFailure(tr("Enter a query or run a Recoll search first."));
        return;
    }
    if (store.isEmpty() || !QFileInfo::exists(store)) {
        showFailure(tr("Choose an existing semantic knowledge store."));
        return;
    }

    const QString script = scriptPath();
    if (!QFileInfo::exists(script)) {
        showFailure(tr("Could not find recoll_ai.py. Set RECOLL_AI_SCRIPT."));
        return;
    }

    QSettings().setValue(settingsKeyStore, store);
    m_standardOutput.clear();
    m_standardError.clear();
    m_operation = operation;
    m_cancelled = false;
    m_answerView->clear();
    m_evidenceList->clear();

    QStringList arguments;
    arguments << script;
    if (operation == Operation::Search) {
        arguments << "search" << "--store" << store << "--json"
                  << "--timeout" << "120" << "--limit" << "5" << query;
        setBusy(true, tr("Retrieving semantic evidence…"));
    } else {
        arguments << "ask" << "--store" << store << "--json"
                  << "--timeout" << "600" << "--evidence-limit" << "2"
                  << "--view" << m_viewCombo->currentData().toString() << query;
        setBusy(true, tr("Retrieving evidence and generating locally…"));
    }

    m_process->setWorkingDirectory(workingDirectory());
    m_process->start(pythonExecutable(), arguments);
}

void AIPerspectiveDock::cancelOperation()
{
    if (m_process->state() == QProcess::NotRunning)
        return;
    m_cancelled = true;
    m_process->terminate();
    m_progress->setFormat(tr("Cancelling…"));
    QTimer::singleShot(1500, m_process, [this]() {
        if (m_process->state() != QProcess::NotRunning)
            m_process->kill();
    });
}

void AIPerspectiveDock::collectStandardOutput()
{
    m_standardOutput += m_process->readAllStandardOutput();
}

void AIPerspectiveDock::collectStandardError()
{
    m_standardError += m_process->readAllStandardError();
}

void AIPerspectiveDock::processFinished(int exitCode, QProcess::ExitStatus exitStatus)
{
    collectStandardOutput();
    collectStandardError();
    if (m_cancelled) {
        setBusy(false, tr("Cancelled"));
        m_operation = Operation::None;
        return;
    }

    QJsonParseError parseError;
    const QJsonDocument document = QJsonDocument::fromJson(
        m_standardOutput.trimmed(), &parseError);
    if (parseError.error != QJsonParseError::NoError || !document.isObject()) {
        QString detail = QString::fromUtf8(m_standardError).trimmed().left(800);
        if (detail.isEmpty())
            detail = tr("The local AI command returned invalid JSON.");
        showFailure(detail);
    } else {
        const QJsonObject response = document.object();
        if (exitStatus != QProcess::NormalExit || exitCode != 0 ||
                response.value("status").toString() == "error") {
            showFailure(response.value("error").toString(
                tr("The local AI command failed.")));
        } else {
            renderResponse(response);
            setBusy(false, tr("Ready"));
        }
    }
    m_operation = Operation::None;
}

void AIPerspectiveDock::processError(QProcess::ProcessError error)
{
    if (error == QProcess::FailedToStart) {
        showFailure(tr("Could not start the local Python runtime. Set RECOLL_AI_PYTHON."));
        m_operation = Operation::None;
    }
}

void AIPerspectiveDock::renderResponse(const QJsonObject& response)
{
    if (m_operation == Operation::Search)
        renderSearch(response);
    else
        renderAnswer(response);
}

void AIPerspectiveDock::renderSearch(const QJsonObject& response)
{
    const QJsonArray results = response.value("results").toArray();
    m_answerView->setHtml(QString("<h3>%1</h3><p>%2</p>")
        .arg(tr("Conceptual evidence"))
        .arg(tr("%1 evidence segments found. Double-click a source below to open it.")
            .arg(results.size())));
    for (int index = 0; index < results.size(); ++index)
        addEvidence(results.at(index).toObject(), index + 1);
}

void AIPerspectiveDock::renderAnswer(const QJsonObject& response)
{
    const QString answer = response.value("answer").toString();
    const bool insufficient = response.value("insufficient_evidence").toBool();
    QString html = QString("<h3>%1</h3><p>%2</p>")
        .arg(m_viewCombo->currentText().toHtmlEscaped())
        .arg(answer.toHtmlEscaped().replace("\n", "<br>"));
    if (insufficient)
        html += QString("<p><b>%1</b></p>").arg(tr("Evidence is insufficient."));
    m_answerView->setHtml(html);

    const QJsonArray citations = response.value("citations").toArray();
    for (int index = 0; index < citations.size(); ++index)
        addEvidence(citations.at(index).toObject(), index + 1);
}

void AIPerspectiveDock::addEvidence(const QJsonObject& evidence, int position)
{
    auto *item = new QListWidgetItem(evidenceLabel(evidence, position), m_evidenceList);
    item->setData(Qt::UserRole, evidence.value("path").toString());
    const QString excerpt = evidence.value("text").toString().simplified();
    const QString segment = evidence.value("segment_id").toString();
    item->setToolTip(QString("%1\n%2\n%3")
        .arg(evidence.value("path").toString(), segment, excerpt.left(700)));
}

void AIPerspectiveDock::openEvidence(QListWidgetItem *item)
{
    if (!item)
        return;
    const QString url = item->data(Qt::UserRole).toString();
    if (!url.isEmpty())
        emit openSourceRequested(url);
}

void AIPerspectiveDock::setBusy(bool busy, const QString& status)
{
    m_searchButton->setEnabled(!busy);
    m_askButton->setEnabled(!busy);
    m_cancelButton->setEnabled(busy);
    m_storeEdit->setEnabled(!busy);
    m_queryEdit->setEnabled(!busy);
    m_viewCombo->setEnabled(!busy);
    if (busy) {
        m_progress->setRange(0, 0);
    } else {
        m_progress->setRange(0, 1);
        m_progress->setValue(status == tr("Ready") ? 1 : 0);
    }
    m_progress->setFormat(status);
}

void AIPerspectiveDock::showFailure(const QString& message)
{
    setBusy(false, tr("Failed"));
    m_answerView->setHtml(QString("<p><b>%1</b></p><p>%2</p>")
        .arg(tr("Local AI operation failed"), message.toHtmlEscaped()));
}

QString AIPerspectiveDock::scriptPath() const
{
    const QString configured = envValue("RECOLL_AI_SCRIPT");
    if (!configured.isEmpty())
        return QDir::fromNativeSeparators(configured);
    return QDir::current().absoluteFilePath("src/semantic/recoll_ai.py");
}

QString AIPerspectiveDock::workingDirectory() const
{
    const QString configured = envValue("RECOLL_AI_WORKDIR");
    if (!configured.isEmpty())
        return QDir::fromNativeSeparators(configured);
    QDir directory = QFileInfo(scriptPath()).absoluteDir();
    directory.cdUp();
    directory.cdUp();
    return directory.absolutePath();
}

QString AIPerspectiveDock::pythonExecutable() const
{
    const QString configured = envValue("RECOLL_AI_PYTHON");
    if (!configured.isEmpty())
        return QDir::fromNativeSeparators(configured);
    const QDir root(workingDirectory());
#ifdef Q_OS_WIN
    const QString local = root.filePath(".venv/Scripts/python.exe");
#else
    const QString local = root.filePath(".venv/bin/python3");
#endif
    return QFileInfo::exists(local) ? local : QString("python");
}
