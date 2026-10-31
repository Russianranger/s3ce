.method public run()V
    .locals 3

    .prologue
    .line 607
    invoke-direct {p0}, Lcom/ideaworks3d/airplay/AirplayThread;->waitForView()V

    .line 608
    const/4 v0, 0x1

    invoke-static {v0}, Ljava/lang/Boolean;->valueOf(Z)Ljava/lang/Boolean;

    move-result-object v0

    iput-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Started:Ljava/lang/Boolean;

    const-string v0, "Native Main ENTER"
    invoke-static {v0}, Lcom/ideaworks3d/thesims3/GameSession;->phase(Ljava/lang/String;)V

    .line 609
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_FileRoot:Ljava/io/File;

    invoke-virtual {v0}, Ljava/io/File;->getAbsolutePath()Ljava/lang/String;

    move-result-object v0

    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayThread;->m_Airplay:Lcom/ideaworks3d/airplay/AirplayActivity;

    invoke-virtual {v1}, Lcom/ideaworks3d/airplay/AirplayActivity;->getPackageResourcePath()Ljava/lang/String;

    move-result-object v1

    invoke-virtual {p0}, Lcom/ideaworks3d/airplay/AirplayThread;->getSampleRate()I

    move-result v2

    invoke-direct {p0, v0, v1, v2}, Lcom/ideaworks3d/airplay/AirplayThread;->runNative(Ljava/lang/String;Ljava/lang/String;I)V

    const-string v0, "Native Main RETURN (normal runNative return)"
    invoke-static {v0}, Lcom/ideaworks3d/thesims3/GameSession;->phase(Ljava/lang/String;)V

    .line 610
    const-string v0, "AirplayThread"

    const-string v1, "Native code done.  Shutting down"

    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 611
    const/4 v0, 0x0

    invoke-direct {p0, v0}, Lcom/ideaworks3d/airplay/AirplayThread;->shuttingDown(Z)V

    .line 612
    return-void
.end method
