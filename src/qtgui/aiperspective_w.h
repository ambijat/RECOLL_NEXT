/* Copyright (C) 2026 Recoll Next contributors
 *
 * This program is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or
 * (at your option) any later version.
 */
#ifndef AIPERSPECTIVE_W_H
#define AIPERSPECTIVE_W_H

#include <QByteArray>
#include <QDockWidget>
#include <QProcess>
#include <QString>

class QComboBox;
class QJsonArray;
class QJsonObject;
class QLineEdit;
class QListWidget;
class QListWidgetItem;
class QProgressBar;
class QPushButton;
class QTextBrowser;

class AIPerspectiveDock : public QDockWidget {
    Q_OBJECT

public:
    explicit AIPerspectiveDock(QWidget *parent = nullptr);

public slots:
    void setQuery(const QString& query);

signals:
    void openSourceRequested(const QString& url);

private slots:
    void browseStore();
    void startSearch();
    void startAsk();
    void cancelOperation();
    void collectStandardOutput();
    void collectStandardError();
    void processFinished(int exitCode, QProcess::ExitStatus exitStatus);
    void processError(QProcess::ProcessError error);
    void openEvidence(QListWidgetItem *item);

private:
    enum class Operation { None, Search, Ask };

    void startOperation(Operation operation);
    void setBusy(bool busy, const QString& status = QString());
    void renderResponse(const QJsonObject& response);
    void renderSearch(const QJsonObject& response);
    void renderAnswer(const QJsonObject& response);
    void addEvidence(const QJsonObject& evidence, int position);
    void showFailure(const QString& message);
    QString pythonExecutable() const;
    QString scriptPath() const;
    QString workingDirectory() const;

    QLineEdit *m_queryEdit{nullptr};
    QLineEdit *m_storeEdit{nullptr};
    QComboBox *m_modeCombo{nullptr};
    QComboBox *m_viewCombo{nullptr};
    QPushButton *m_searchButton{nullptr};
    QPushButton *m_askButton{nullptr};
    QPushButton *m_cancelButton{nullptr};
    QProgressBar *m_progress{nullptr};
    QTextBrowser *m_answerView{nullptr};
    QListWidget *m_evidenceList{nullptr};
    QProcess *m_process{nullptr};
    QByteArray m_standardOutput;
    QByteArray m_standardError;
    Operation m_operation{Operation::None};
    bool m_cancelled{false};
};

#endif // AIPERSPECTIVE_W_H
