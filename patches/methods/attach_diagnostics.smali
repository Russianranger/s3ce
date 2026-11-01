.method public createView(Z)V
    .locals 3

    .prologue
    const-string v2, "AirplayActivity"

    .line 58
    const-string v0, "AirplayActivity"

    new-instance v0, Ljava/lang/StringBuilder;

    invoke-direct {v0}, Ljava/lang/StringBuilder;-><init>()V

    const-string v1, "createView: gl="

    invoke-virtual {v0, v1}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0, p1}, Ljava/lang/StringBuilder;->append(Z)Ljava/lang/StringBuilder;

    move-result-object v0

    invoke-virtual {v0}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;

    move-result-object v0

    invoke-static {v2, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 59
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayActivity;->m_View:Lcom/ideaworks3d/airplay/AirplayView;

    if-eqz v0, :cond_0

    .line 61
    const-string v0, "AirplayActivity"

    const-string v0, "Freeing the existing View"

    invoke-static {v2, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 63
    const/4 v0, 0x0

    iput-object v0, p0, Lcom/ideaworks3d/airplay/AirplayActivity;->m_View:Lcom/ideaworks3d/airplay/AirplayView;

    .line 64
    invoke-static {}, Ljava/lang/System;->gc()V

    .line 66
    :cond_0
    new-instance v0, Lcom/ideaworks3d/airplay/AirplayView;

    invoke-direct {v0, p0, p1}, Lcom/ideaworks3d/airplay/AirplayView;-><init>(Lcom/ideaworks3d/airplay/AirplayActivity;Z)V

    iput-object v0, p0, Lcom/ideaworks3d/airplay/AirplayActivity;->m_View:Lcom/ideaworks3d/airplay/AirplayView;

    .line 67
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayActivity;->m_View:Lcom/ideaworks3d/airplay/AirplayView;

    invoke-static {p0, v0}, Lcom/ideaworks3d/thesims3/GameViewport;->install(Landroid/app/Activity;Landroid/view/View;)V

    invoke-static {p0}, Lcom/ideaworks3d/thesims3/GameDiagnostics;->attach(Landroid/app/Activity;)V

    .line 68
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayActivity;->m_AirplayThread:Lcom/ideaworks3d/airplay/AirplayThread;

    if-eqz v0, :cond_1

    .line 69
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayActivity;->m_AirplayThread:Lcom/ideaworks3d/airplay/AirplayThread;

    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayActivity;->m_View:Lcom/ideaworks3d/airplay/AirplayView;

    invoke-virtual {v0, v1}, Lcom/ideaworks3d/airplay/AirplayThread;->setView(Lcom/ideaworks3d/airplay/AirplayView;)V

    .line 70
    :cond_1
    return-void
.end method
