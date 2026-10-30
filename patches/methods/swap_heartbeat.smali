.method public glSwapBuffers()V
    .locals 2

    .prologue
    .line 535
    sget-object v0, Lcom/ideaworks3d/airplay/AirplayView;->m_AirplayGL:Lcom/ideaworks3d/airplay/AirplayGL;

    invoke-virtual {v0}, Lcom/ideaworks3d/airplay/AirplayGL;->started()Z

    move-result v0

    if-nez v0, :cond_0

    .line 537
    const-string v0, "AirplayView"

    const-string v1, "glSwapBuffers called before glInit"

    invoke-static {v0, v1}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 541
    :goto_0
    return-void

    .line 540
    :cond_0
    sget-object v0, Lcom/ideaworks3d/airplay/AirplayView;->m_AirplayGL:Lcom/ideaworks3d/airplay/AirplayGL;

    invoke-virtual {v0}, Lcom/ideaworks3d/airplay/AirplayGL;->swap()V

    invoke-static {}, Lcom/ideaworks3d/thesims3/GameDiagnostics;->frame()V

    goto :goto_0
.end method
