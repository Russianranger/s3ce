.method public doDraw()V
    .locals 10

    .prologue
    const/4 v9, 0x0

    const/4 v2, 0x0

    const-string v8, "AirplayView"

    .line 758
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_FullScreenBitmap:Landroid/graphics/Bitmap;

    if-nez v0, :cond_0

    .line 760
    const-string v0, "AirplayView"

    const-string v0, "doDraw: no m_FullScreenBitmap"

    invoke-static {v8, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    .line 783
    :goto_0
    return-void

    .line 764
    :cond_0
    iget-boolean v0, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_UseGL:Z

    if-eqz v0, :cond_1

    .line 766
    const-string v0, "AirplayView"

    const-string v0, "doDraw: ignoring due to GL mode"

    invoke-static {v8, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    goto :goto_0

    .line 771
    :cond_1
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_FullScreenBitmap:Landroid/graphics/Bitmap;

    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_Pixels:[I

    iget v3, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_Width:I

    iget v6, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_Width:I

    iget v7, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_Height:I

    move v4, v2

    move v5, v2

    invoke-virtual/range {v0 .. v7}, Landroid/graphics/Bitmap;->setPixels([IIIIIII)V

    .line 774
    iget-object v0, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_SurfaceHolder:Landroid/view/SurfaceHolder;

    invoke-interface {v0}, Landroid/view/SurfaceHolder;->lockCanvas()Landroid/graphics/Canvas;

    move-result-object v0

    .line 775
    if-nez v0, :cond_2

    .line 777
    const-string v0, "AirplayView"

    const-string v0, "doDraw: fail to lock canvas"

    invoke-static {v8, v0}, Landroid/util/Log;->i(Ljava/lang/String;Ljava/lang/String;)I

    goto :goto_0

    .line 780
    :cond_2
    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_FullScreenBitmap:Landroid/graphics/Bitmap;

    iget-object v2, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_Paint:Landroid/graphics/Paint;

    invoke-virtual {v0, v1, v9, v9, v2}, Landroid/graphics/Canvas;->drawBitmap(Landroid/graphics/Bitmap;FFLandroid/graphics/Paint;)V

    .line 781
    iget-object v1, p0, Lcom/ideaworks3d/airplay/AirplayView;->m_SurfaceHolder:Landroid/view/SurfaceHolder;

    invoke-interface {v1, v0}, Landroid/view/SurfaceHolder;->unlockCanvasAndPost(Landroid/graphics/Canvas;)V

    invoke-static {}, Lcom/ideaworks3d/thesims3/GameDiagnostics;->frame()V

    goto :goto_0
.end method
